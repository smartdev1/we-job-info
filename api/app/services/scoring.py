"""Offer scoring engine."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

PRIORITY_SECTORS = {"informatique", "tech", "data", "cybersécurité", "cybersecurite", "it"}
PRIORITY_CITIES = {"abidjan", "cocody", "plateau"}

KEY_FIELDS = (
    "title", "company", "city", "contract_type", "education_level",
    "experience", "sector", "description", "how_to_apply",
)


def _is_filled(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return len(value) > 0
    return True


def compute_score(offer: Any) -> float:
    """Compute a 0..1 score for an offer (dict or ORM-like)."""
    def get(key: str) -> Any:
        if isinstance(offer, dict):
            return offer.get(key)
        return getattr(offer, key, None)

    score = 0.0

    # Completeness (up to 0.4)
    filled = sum(1 for f in KEY_FIELDS if _is_filled(get(f)))
    score += 0.4 * (filled / len(KEY_FIELDS))

    # Freshness (up to 0.2)
    created = get("created_at")
    if isinstance(created, datetime):
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        age_days = (datetime.now(timezone.utc) - created).days
        if 0 <= age_days <= 7:
            score += 0.2
        elif 8 <= age_days <= 30:
            score += 0.1

    # Deadline presence (0.1)
    if _is_filled(get("deadline")):
        score += 0.1

    # Contact presence (0.1)
    if _is_filled(get("contact_email")) or _is_filled(get("application_url")):
        score += 0.1

    # Priority sector/city (0.2)
    sector = (get("sector") or "").lower() if isinstance(get("sector"), str) else ""
    city = (get("city") or "").lower() if isinstance(get("city"), str) else ""
    if sector in PRIORITY_SECTORS or city in PRIORITY_CITIES:
        score += 0.2

    return round(min(max(score, 0.0), 1.0), 4)