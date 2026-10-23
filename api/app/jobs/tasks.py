"""Procrastinate tasks for the collection pipeline."""

from __future__ import annotations

import logging
from typing import Any

from app.jobs.app import app
from app.jobs.collect_source import collect_source
from app.sources.connector import list_sources
from app.services.offer_service import _extract_fields_from_html

logger = logging.getLogger(__name__)


@app.task(retry=3, queue="collect", lock="collect:{source_id}")
def collect_source_task(source_id: str) -> list[Any]:
    """Collect items from a source and enqueue an extract job per item."""
    results = collect_source(source_id)
    for item in results:
        raw = item.get("raw_text") if isinstance(item, dict) else item
        origin_url = item.get("origin_url") if isinstance(item, dict) else None
        if isinstance(raw, str):
            extract_task.defer(raw_text=raw)
        # Persist collected offer (idempotent) when a DB is available.
        try:
            from app.storage.offers import persist_collected_offer_sync

            persist_collected_offer_sync(source_id=source_id, origin_url=origin_url, raw_text=raw if isinstance(raw, str) else None)
        except Exception as exc:  # noqa: BLE001
            logger.warning("collect: persistence skipped/failed for %s: %s", source_id, exc)
    return results


@app.task(retry=3, queue="process")
def fetch_task(url: str) -> str:
    """Fetch the raw content of a single offer URL."""
    import urllib.request

    req = urllib.request.Request(url, headers={"User-Agent": "we-info-jobs-bot/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8", errors="replace")


@app.task(retry=3, queue="process")
def extract_task(raw_text: str) -> dict[str, Any]:
    """Extract a structured offer from raw text via the LLM provider.

    Étape 1 : prétraitement HTML pour extraire les champs visibles (titre,
    compagnie, localisation, date limite, URL candidature, type de contrat).
    Ces valeurs sont prépendues au texte avant envoi au LLM, ce qui augmente
 considérablement le taux de remplissage des champs d'extraction.
    """
    from app.core.llm import get_llm_provider
    from app.extraction.schema import OffreExtraite

    # --- ÉTAPE 1 : Prétraitement HTML ---
    extracted = _extract_fields_from_html(raw_text)

    # Construire un contexte enrichi pour le prompt
    context_parts = []
    if extracted["title"]:
        context_parts.append(f"TITRE: {extracted['title']}")
    if extracted["company"]:
        context_parts.append(f"ENTREPRISE: {extracted['company']}")
    if extracted["location"]:
        context_parts.append(f"LOCALISATION: {extracted['location']}")
    if extracted["deadline"]:
        context_parts.append(f"DATE LIMITE: {extracted['deadline']}")
    if extracted["application_url"]:
        context_parts.append(f"LIEN CANDIDATURE: {extracted['application_url']}")
    if extracted["contract_type"]:
        context_parts.append(f"TYPE DE CONTRAT: {extracted['contract_type']}")

    context = "\n".join(context_parts) if context_parts else ""

    # --- ÉTAPE 2 : Concaténer contexte + contenu brut ---
    # Si on a extrait des champs, on les prépend au contenu pour guider le LLM
    if context:
        enriched_text = f"{context}\n\nCONTENU DE L'OFFRE:\n{raw_text}"
    else:
        enriched_text = raw_text

    # --- ÉTAPE 3 : Extraction LLM ---
    provider = get_llm_provider()
    result = provider.extraire(enriched_text)
    return result.model_dump() if hasattr(result, "model_dump") else dict(result)


@app.task(retry=3, queue="process")
def normalize_task(offer: dict[str, Any]) -> dict[str, Any]:
    """Normalize an extracted offer (strip, lowercase keys, defaults)."""
    return {k: (v.strip() if isinstance(v, str) else v) for k, v in offer.items()}


@app.task(queue="maintenance")
def expire_offers_task() -> int:
    """Mark offers whose deadline passed as 'expiree'. Idempotent.

    Uses the database server clock (NOW()) to avoid naive/aware tz mismatches.
    """
    from sqlalchemy import create_engine, text

    from app.core.config import get_settings

    settings = get_settings()
    url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://").replace(
        "sqlite+aiosqlite:///", "sqlite:///"
    )
    url = url.replace("ssl=require", "sslmode=require").replace("ssl=prefer", "sslmode=prefer")
    engine = create_engine(url)
    with engine.begin() as conn:
        result = conn.execute(
            text(
                "UPDATE offers SET status = 'expiree' "
                "WHERE deadline IS NOT NULL AND deadline < NOW() "
                "AND status <> 'expiree'"
            )
        )
        count = result.rowcount or 0
    logger.info("expire_offers: marked %d offers expired", count)
    return count


@app.task(queue="maintenance")
def check_sources_health_task() -> dict[str, Any]:
    """Probe all registered sources and alert on silent failures."""
    import os
    from datetime import datetime, timedelta, timezone

    from app.sources.connector import list_sources, get_connector

    silence_days = int(os.getenv("SOURCE_SILENCE_DAYS", "3"))
    failure_threshold = int(os.getenv("SOURCE_FAILURE_THRESHOLD", "3"))
    now = datetime.now(timezone.utc)
    report: dict[str, Any] = {}
    alerts: list[str] = []

    for sid in list_sources():
        try:
            health = get_connector(sid).sante()
        except Exception as exc:  # noqa: BLE001
            health = {"status": "error", "error": str(exc)}
        report[sid] = health

        last_success = health.get("last_success_at")
        failures = health.get("failure_count", 0)
        stale = False
        if last_success:
            try:
                ls = datetime.fromisoformat(last_success.replace("Z", "+00:00"))
                stale = (now - ls) > timedelta(days=silence_days)
            except ValueError:
                stale = False

        if stale or failures >= failure_threshold:
            msg = f"[ALERT] source '{sid}' unhealthy: failures={failures}, stale={stale}, last_error={health.get('last_error')}"
            logger.warning(msg)
            alerts.append(msg)
            _send_alert(msg)

    report["_alerts"] = alerts
    return report


@app.periodic(cron="0 8,20 * * *", periodic_id="offer-maintenance")
@app.task(queue="maintenance")
def run_maintenance_task(timestamp: int) -> dict[str, Any]:
    """Periodic maintenance: collect from every source, expire offers, health-check.

    Failures of an individual source are isolated so one bad source does not
    abort the whole maintenance run.
    """
    results: dict[str, Any] = {"sources": {}, "expired": None, "health": None}

    sources = list_sources()
    for source_id in sources:
        try:
            collect_source_task.defer(source_id=source_id)
            results["sources"][source_id] = "enqueued"
        except Exception as exc:  # noqa: BLE001
            logger.exception("maintenance: failed to enqueue collect for %s", source_id)
            results["sources"][source_id] = f"error: {exc}"

    try:
        expire_offers_task.defer()
        results["expired"] = "enqueued"
    except Exception as exc:  # noqa: BLE001
        logger.exception("maintenance: expire_offers_task failed")
        results["expired"] = f"error: {exc}"

    try:
        check_sources_health_task.defer()
        results["health"] = "enqueued"
    except Exception as exc:  # noqa: BLE001
        logger.exception("maintenance: check_sources_health_task failed")
        results["health"] = f"error: {exc}"

    logger.info("maintenance run %s completed: %s", timestamp, results)
    return results


def _send_alert(message: str) -> None:
    """Send alert via configured channel (webhook or Telegram), else log only."""
    import os
    import urllib.request
    import urllib.parse
    import json

    webhook = os.getenv("ALERT_WEBHOOK_URL")
    if webhook:
        try:
            data = json.dumps({"text": message}).encode("utf-8")
            req = urllib.request.Request(webhook, data=data, headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=10)
            return
        except Exception as exc:  # noqa: BLE001
            logger.error("alert webhook failed: %s", exc)

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat = os.getenv("TELEGRAM_CHAT_ID")
    if token and chat:
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            data = urllib.parse.urlencode({"chat_id": chat, "text": message}).encode("utf-8")
            urllib.request.urlopen(url, data=data, timeout=10)
            return
        except Exception as exc:  # noqa: BLE001
            logger.error("telegram alert failed: %s", exc)

    logger.info("no alert channel configured; alert logged only")