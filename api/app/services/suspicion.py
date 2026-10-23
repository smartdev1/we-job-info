"""Suspicion rules for scam detection."""

from __future__ import annotations

import re
from typing import Any

RULES: list[tuple[str, Any]] = [
    ("demande de paiement", lambda o, g: bool(re.search(r"paiement|frais|argent|mobile money|orange money|mtn money", (g("description") or "") + " " + (g("how_to_apply") or ""), re.I))),
    ("email gratuit pour grande entreprise", lambda o, g: bool(re.search(r"gmail\.com|yahoo\.fr|hotmail\.com|outlook\.com", g("contact_email") or "", re.I)) and bool(g("company"))),
    ("salaire irréaliste", lambda o, g: bool(re.search(r"(salaire|rémunération|paie|paye).{0,30}\d{7,}|\d{7,}.{0,30}(salaire|rémunération|fcfa|xof|euros?)", (g("description") or "") + " " + (g("title") or ""), re.I))),
    ("aucune entreprise identifiable", lambda o, g: not g("company")),
    ("contact uniquement par messagerie privée", lambda o, g: bool(re.search(r"whatsapp|telegram|dm|message priv", (g("how_to_apply") or "") + " " + (g("description") or ""), re.I)) and not (g("contact_email") and str(g("contact_email")).strip()) and not (g("application_url") and str(g("application_url")).strip())),
    ("urgence excessive", lambda o, g: bool(re.search(r"urgent|immédiat|aujourd'hui|dans les 24h", (g("description") or "") + " " + (g("title") or ""), re.I))),
]


def check_suspicion(offer: Any) -> tuple[bool, list[str]]:
    """Return (suspect, reasons) for an offer."""
    def get(key: str) -> Any:
        if isinstance(offer, dict):
            return offer.get(key)
        return getattr(offer, key, None)

    reasons = [name for name, pred in RULES if pred(offer, get)]
    return (len(reasons) > 0, reasons)