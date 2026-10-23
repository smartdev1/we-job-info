"""Manual collection run: fetch every source and store the offers in the database.

Runs the same pipeline as the scheduled worker (collect -> fetch -> store),
but synchronously and with a readable report, so a collection can be checked
by hand at any time.

Usage:
    uv run python scripts/collect_offers.py
    uv run python scripts/collect_offers.py --source emploi_ci --source jobivoire
    uv run python scripts/collect_offers.py --dry-run

The run is idempotent: an offer is matched on its origin URL first, then on
its fingerprint, so running it twice does not create duplicates. It writes to
the database configured by DATABASE_URL, which in development points at the
production Neon instance.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.exc import DBAPIError, InterfaceError, OperationalError  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

import app.sources  # noqa: F401,E402 - registers the connectors
from app.core.db import SessionLocal  # noqa: E402
from app.models import Offer, RawDocument, Source  # noqa: E402
from app.sources.base import sector_for_title  # noqa: E402
from app.sources.connector import get_connector, list_sources  # noqa: E402
from app.services.dedup import fingerprint as compute_fingerprint  # noqa: E402
from app.storage.offers import upsert_collected_offer  # noqa: E402

REQUEST_DELAY_SECONDS = 1.5
# One detail page per candidate: pace them so a source is not hammered.
OFFER_DELAY_SECONDS = 0.5


@dataclass
class SourceStats:
    source_id: str
    collected: int = 0
    inserted: int = 0
    updated: int = 0
    on_theme: int = 0
    error: str | None = None
    failures: list[str] = field(default_factory=list)


async def _ensure_source(db: AsyncSession, source_id: str) -> uuid.UUID:
    """Return the id of the source row, creating it the first time."""
    result = await db.execute(select(Source).where(Source.name == source_id))
    source = result.scalar_one_or_none()
    if source is None:
        source = Source(
            name=source_id,
            type="html",
            config={"connector": source_id},
            active=True,
        )
        db.add(source)
        await db.flush()
    return source.id


async def _ensure_raw_document(
    db: AsyncSession,
    *,
    source_uuid: uuid.UUID,
    url: str,
    content: str,
) -> RawDocument:
    """Store the raw page, reusing the row when the content was already seen."""
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    result = await db.execute(
        select(RawDocument).where(RawDocument.content_hash == content_hash)
    )
    document = result.scalar_one_or_none()
    if document is None:
        document = RawDocument(
            source_id=source_uuid,
            url=url,
            content_type="text/html",
            content=content,
            content_hash=content_hash,
        )
        db.add(document)
        await db.flush()
    return document


async def _find_existing(
    db: AsyncSession, *, url: str | None, fingerprint: str | None
) -> Offer | None:
    """Find the offer already stored under the same origin URL or fingerprint."""
    if url:
        result = await db.execute(select(Offer).where(Offer.origin_url == url))
        found = result.scalar_one_or_none()
        if found is not None:
            return found
    if fingerprint:
        result = await db.execute(select(Offer).where(Offer.fingerprint == fingerprint))
        found = result.scalar_one_or_none()
        if found is not None:
            return found
    return None


async def collect_source_into_db(source_id: str) -> SourceStats:
    """Collect one source and persist everything it advertises."""
    stats = SourceStats(source_id=source_id)
    connector = get_connector(source_id)

    async with SessionLocal() as db:
        source_uuid = await _ensure_source(db, source_id)
        await db.commit()

    try:
        candidates = connector.lister_candidates()
    except Exception as exc:  # noqa: BLE001 - one broken source must not stop the run
        stats.error = f"{type(exc).__name__}: {exc}"
        async with SessionLocal() as db:
            await _record_failure(db, source_uuid, stats.error)
            await db.commit()
        return stats

    stats.collected = len(candidates)

    for candidate in candidates:
        if stats.inserted + stats.updated:
            await asyncio.sleep(OFFER_DELAY_SECONDS)
        url = getattr(candidate, "url", None)
        title = getattr(candidate, "title", None)
        done = stats.inserted + stats.updated + 1
        print(f"  [{done:>3}/{len(candidates)}] {_ascii(title or url or '')[:70]}", flush=True)
        try:
            content = connector.recuperer(candidate)
        except Exception as exc:  # noqa: BLE001 - keep collecting the rest
            stats.failures.append(f"{url}: {type(exc).__name__}: {exc}")
            continue

        # The write runs in its own short-lived session on purpose. A session
        # held open across the HTTP fetch keeps a pooled connection checked
        # out while it sits idle, and the Neon serverless pooler closes it:
        # "connection was closed in the middle of operation". Releasing the
        # connection between the fetch and the write avoids that entirely, and
        # pool_pre_ping revalidates it on the next checkout.
        stored = False
        for attempt in (1, 2):
            try:
                async with SessionLocal() as db:
                    document = await _ensure_raw_document(
                        db, source_uuid=source_uuid, url=url or "", content=content
                    )

                    sector = sector_for_title(title) if title else None

                    # Idempotence keys: origin URL first, then the fingerprint.
                    # The fingerprint is computed here so that the "inserted vs
                    # updated" count reflects what really happened.
                    # Parse the detail page to get company/city for a reliable fingerprint.
                    detail_company = None
                    detail_city = None
                    try:
                        detail = connector.parse_detail(content)
                        detail_company = getattr(detail, "company", None)
                        detail_city = getattr(detail, "city", None)
                    except Exception:
                        pass
                    fingerprint = compute_fingerprint(detail_company, title, detail_city)
                    already_there = await _find_existing(db, url=url, fingerprint=fingerprint)

                    extra: dict[str, Any] = {"raw_document_id": document.id}
                    if sector:
                        # Never overwrite a sector an earlier extraction set.
                        extra["sector"] = sector

                    await upsert_collected_offer(
                        db,
                        source_id=source_uuid,
                        origin_url=url,
                        title=title,
                        company=detail_company,
                        city=detail_city,
                        fingerprint=fingerprint,
                        raw_text=content,
                        **extra,
                    )
                    await db.commit()

                if sector:
                    stats.on_theme += 1
                if already_there:
                    stats.updated += 1
                else:
                    stats.inserted += 1
                stored = True
                break
            except (DBAPIError, InterfaceError, OperationalError) as exc:  # noqa: BLE001
                # The pooled connection was dropped by the server: let the pool
                # hand out a fresh one and try once more.
                if attempt == 2:
                    stats.failures.append(f"{url}: {type(exc).__name__}: {exc}")
                continue
        if not stored:
            continue

    async with SessionLocal() as db:
        await _record_success(db, source_uuid)
        await db.commit()
    return stats


async def _record_success(db: AsyncSession, source_uuid: uuid.UUID) -> None:
    from datetime import datetime, timezone

    result = await db.execute(select(Source).where(Source.id == source_uuid))
    source = result.scalar_one_or_none()
    if source is not None:
        source.last_success_at = datetime.now(tz=timezone.utc)
        source.consecutive_failures = 0
        source.last_error = None


async def _record_failure(db: AsyncSession, source_uuid: uuid.UUID, error: str) -> None:
    result = await db.execute(select(Source).where(Source.id == source_uuid))
    source = result.scalar_one_or_none()
    if source is not None:
        source.consecutive_failures = (source.consecutive_failures or 0) + 1
        source.last_error = error


def _ascii(text: str) -> str:
    return text.encode("ascii", "backslashreplace").decode("ascii")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect offers from the sources into the database.")
    parser.add_argument(
        "--source",
        action="append",
        default=None,
        help="Only collect this source id (repeatable). Defaults to every source.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Collect but do not write anything.")
    return parser.parse_args()


async def _run(source_ids: list[str], dry_run: bool) -> int:
    stats_list: list[SourceStats] = []
    for index, source_id in enumerate(source_ids):
        if index:
            await asyncio.sleep(REQUEST_DELAY_SECONDS)
        print(f"[{source_id}] collecting...", flush=True)
        if dry_run:
            connector = get_connector(source_id)
            stats = SourceStats(source_id=source_id)
            try:
                candidates = connector.lister_candidates()
                stats.collected = len(candidates)
                stats.on_theme = sum(1 for c in candidates if sector_for_title(c.title or ""))
            except Exception as exc:  # noqa: BLE001
                stats.error = f"{type(exc).__name__}: {exc}"
            stats_list.append(stats)
        else:
            stats_list.append(await collect_source_into_db(source_id))

    header = f"{'source':<16}{'collected':>10}{'inserted':>10}{'updated':>9}{'on-theme':>10}  status"
    print(header)
    print("-" * len(header))
    for stats in stats_list:
        status = "ERROR" if stats.error else ("ok" if not stats.failures else "partial")
        print(
            f"{stats.source_id:<16}{stats.collected:>10}{stats.inserted:>10}"
            f"{stats.updated:>9}{stats.on_theme:>10}  {status}"
        )
        if stats.error:
            print(f"    {stats.error}")
        for failure in stats.failures[:5]:
            print(f"    ! {failure}")

    total_inserted = sum(s.inserted for s in stats_list)
    total_updated = sum(s.updated for s in stats_list)
    print()
    print(f"inserted={total_inserted} updated={total_updated}")
    if dry_run:
        print("dry run: nothing was written.")
    return 1 if any(s.error for s in stats_list) else 0


def main() -> int:
    args = _parse_args()
    source_ids = args.source or list_sources()
    unknown = [s for s in source_ids if s not in list_sources()]
    if unknown:
        print(f"Unknown source(s): {', '.join(unknown)}", file=sys.stderr)
        print(f"Known sources: {', '.join(list_sources())}", file=sys.stderr)
        return 2
    return asyncio.run(_run(source_ids, args.dry_run))


if __name__ == "__main__":
    raise SystemExit(main())
