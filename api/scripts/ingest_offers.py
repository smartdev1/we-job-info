"""Ingest the offers of the live sources into the database, field by field.

The scheduled collection (``scripts/collect_offers.py``) stores the raw HTML
of the detail page in ``offers.description``: it keeps the bytes, but none of
the information the page actually carries. This script fetches the same
detail pages, extracts the fields with the per-site parsers and writes them
into the matching columns of the ``offers`` table, then refreshes the score
and the suspicion reasons.

Usage:
    uv run python scripts/ingest_offers.py
    uv run python scripts/ingest_offers.py --source jobivoire --source emploi_ci
    uv run python scripts/ingest_offers.py --limit 5 --dry-run

The run is idempotent: an offer is matched on its origin URL first, then on
its fingerprint, so running it twice updates the same rows instead of
duplicating them. The pages that were already collected keep their raw
document: only the columns of the offer are rewritten.

It writes to the database configured by DATABASE_URL.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.exc import DBAPIError, InterfaceError, OperationalError  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

import app.sources  # noqa: F401,E402 - registers the connectors
from app.core.db import SessionLocal  # noqa: E402
from app.ingestion.persist import (  # noqa: E402
    ensure_source,
    persist_offer_detail,
)
from app.sources.connector import get_connector, list_sources  # noqa: E402
from app.sources.detail import OfferDetail  # noqa: E402

# Pace between two detail pages of the same source, and between two sources.
OFFER_DELAY_SECONDS = 0.4
SOURCE_DELAY_SECONDS = 1.5

# Fields reported in the summary, in the order they are displayed.
REPORTED_FIELDS = (
    "title",
    "company",
    "location",
    "city",
    "country",
    "contract_type",
    "education_level",
    "experience",
    "sector",
    "description",
    "missions",
    "profile",
    "benefits",
    "how_to_apply",
    "contact_email",
    "application_url",
    "deadline",
)


@dataclass
class SourceStats:
    source_id: str
    listed: int = 0
    fetched: int = 0
    created: int = 0
    updated: int = 0
    failed: int = 0
    suspicious: int = 0
    error: str | None = None
    failures: list[str] = field(default_factory=list)
    fill_rate: dict[str, int] = field(default_factory=dict)


def _ascii(text: str) -> str:
    return text.encode("ascii", "backslashreplace").decode("ascii")


def _is_filled(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple)):
        return bool(value)
    return True


async def _ingest_one(
    db: AsyncSession,
    *,
    source_uuid,
    connector,
    candidate,
) -> tuple[bool, bool, bool, OfferDetail]:
    """Fetch, parse and persist one offer. Returns (created, updated, suspect)."""
    html = connector.recuperer(candidate)
    detail: OfferDetail = connector.parse_detail(html)
    result = await persist_offer_detail(
        db,
        source_uuid=source_uuid,
        detail=detail,
        origin_url=candidate.url,
        raw_html=html,
    )
    return result.created, not result.created, result.suspicious, detail


async def ingest_source(
    source_id: str,
    *,
    limit: int | None = None,
    dry_run: bool = False,
) -> SourceStats:
    """Ingest every offer of one source."""
    stats = SourceStats(source_id=source_id)
    connector = get_connector(source_id)

    try:
        candidates = connector.lister_candidates()
    except Exception as exc:  # noqa: BLE001 - one broken source must not stop the run
        stats.error = f"{type(exc).__name__}: {exc}"
        return stats

    if limit is not None:
        candidates = candidates[:limit]
    stats.listed = len(candidates)

    source_uuid = None
    if not dry_run:
        async with SessionLocal() as db:
            source_uuid = await ensure_source(db, source_id)
            await db.commit()

    for index, candidate in enumerate(candidates):
        title = _ascii(candidate.title or candidate.url)[:70]
        print(f"  [{index + 1:>3}/{len(candidates)}] {title}", flush=True)

        if dry_run:
            try:
                html = connector.recuperer(candidate)
                detail = connector.parse_detail(html)
            except Exception as exc:  # noqa: BLE001
                stats.failed += 1
                stats.failures.append(f"{candidate.url}: {type(exc).__name__}: {exc}")
                continue
            stats.fetched += 1
            for name in REPORTED_FIELDS:
                if _is_filled(getattr(detail, name, None)):
                    stats.fill_rate[name] = stats.fill_rate.get(name, 0) + 1
            continue

        # The write runs in its own short-lived session: a session held open
        # across the HTTP fetch keeps a pooled connection checked out while it
        # idles, and the Neon serverless pooler closes it in the middle of
        # the operation.
        stored = False
        for attempt in (1, 2):
            try:
                async with SessionLocal() as db:
                    created, updated, suspect, detail = await _ingest_one(
                        db,
                        source_uuid=source_uuid,
                        connector=connector,
                        candidate=candidate,
                    )
                    await db.commit()
                stats.fetched += 1
                stats.created += int(created)
                stats.updated += int(updated)
                stats.suspicious += int(suspect)
                for name in REPORTED_FIELDS:
                    if _is_filled(getattr(detail, name, None)):
                        stats.fill_rate[name] = stats.fill_rate.get(name, 0) + 1
                stored = True
                break
            except (DBAPIError, InterfaceError, OperationalError) as exc:  # noqa: BLE001
                # The pooled connection was dropped by the server: let the
                # pool hand out a fresh one and try once more.
                if attempt == 2:
                    stats.failed += 1
                    stats.failures.append(
                        f"{candidate.url}: {type(exc).__name__}: {exc}"
                    )
                continue
            except Exception as exc:  # noqa: BLE001 - keep ingesting the rest
                stats.failed += 1
                stats.failures.append(f"{candidate.url}: {type(exc).__name__}: {exc}")
                break
        if not stored:
            continue
        await asyncio.sleep(OFFER_DELAY_SECONDS)

    return stats


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract the offer fields from the live sources and write them to the database."
    )
    parser.add_argument(
        "--source",
        action="append",
        default=None,
        help="Only ingest this source id (repeatable). Defaults to every source.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only ingest that many offers per source.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and parse but write nothing to the database.",
    )
    return parser.parse_args()


async def _run(source_ids: list[str], limit: int | None, dry_run: bool) -> int:
    stats_list: list[SourceStats] = []
    for index, source_id in enumerate(source_ids):
        if index:
            await asyncio.sleep(SOURCE_DELAY_SECONDS)
        print(f"[{source_id}] ingesting...", flush=True)
        started = time.monotonic()
        stats = await ingest_source(source_id, limit=limit, dry_run=dry_run)
        stats_list.append(stats)
        elapsed = time.monotonic() - started
        print(
            f"[{source_id}] {stats.fetched}/{stats.listed} fetched in {elapsed:.1f}s",
            flush=True,
        )

    header = (
        f"{'source':<16}{'listed':>8}{'fetched':>9}{'created':>9}"
        f"{'updated':>9}{'failed':>8}{'suspect':>9}  status"
    )
    print()
    print(header)
    print("-" * len(header))
    for stats in stats_list:
        status = "ERROR" if stats.error else ("partial" if stats.failed else "ok")
        print(
            f"{stats.source_id:<16}{stats.listed:>8}{stats.fetched:>9}"
            f"{stats.created:>9}{stats.updated:>9}{stats.failed:>8}"
            f"{stats.suspicious:>9}  {status}"
        )
        if stats.error:
            print(f"    {stats.error}")
        for failure in stats.failures[:5]:
            print(f"    ! {failure}")
        if stats.failures[5:]:
            print(f"    ! ... +{len(stats.failures) - 5} more failures")

    # Field coverage: how many offers of the run carry each field.
    total = sum(s.fetched for s in stats_list)
    if total:
        print()
        print(f"field coverage over {total} offers:")
        for name in REPORTED_FIELDS:
            filled = sum(s.fill_rate.get(name, 0) for s in stats_list)
            share = 100.0 * filled / total
            bar = "#" * int(round(share / 5))
            print(f"  {name:<18}{filled:>5}/{total:<6}{share:>6.1f}%  {bar}")

    print()
    print(
        f"created={sum(s.created for s in stats_list)} "
        f"updated={sum(s.updated for s in stats_list)} "
        f"failed={sum(s.failed for s in stats_list)}"
    )
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
    return asyncio.run(_run(source_ids, args.limit, args.dry_run))


if __name__ == "__main__":
    raise SystemExit(main())
