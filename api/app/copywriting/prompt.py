"""Prompt construction for WhatsApp copywriting variants."""

from __future__ import annotations

from typing import Any


_SEPARATOR = "---VARIANT---"


def build_prompt(offer: Any, style: str | None) -> str:
    source_url = getattr(offer, "origin_url", None) or getattr(offer, "application_url", None)
    facts = {
        "title": getattr(offer, "title", None),
        "company": getattr(offer, "company", None),
        "location": getattr(offer, "location", None) or getattr(offer, "city", None),
        "contract_type": getattr(offer, "contract_type", None),
        "sector": getattr(offer, "sector", None),
        "description": getattr(offer, "description", None),
        "missions": getattr(offer, "missions", None),
        "profile": getattr(offer, "profile", None),
        "benefits": getattr(offer, "benefits", None),
        "how_to_apply": getattr(offer, "how_to_apply", None),
        "contact_email": getattr(offer, "contact_email", None),
        "application_url": getattr(offer, "application_url", None),
        "deadline": getattr(offer, "deadline", None),
    }
    style_block = style or "(no style guide provided)"
    return (
        "You write WhatsApp messages for a job offer. Produce exactly 3 distinct variants.\n"
        "Formatting: WhatsApp only (*bold*, _italic_). No markdown links beyond the source URL.\n"
        "Use ONLY facts present in the offer below. Do NOT invent salary, contact, dates, or any other detail.\n"
        "Every variant MUST include the source link at the end.\n"
        "Separate variants with the exact token: " + _SEPARATOR + "\n"
        "Do not add any text outside the variants.\n\n"
        f"Style guide:\n{style_block}\n\n"
        f"Offer facts (JSON):\n{facts}\n\n"
        f"Source link to include: {source_url}\n"
    )


def parse_variants(raw: str, source_url: str | None) -> list[str]:
    parts = [p.strip() for p in raw.split(_SEPARATOR) if p.strip()]
    if len(parts) < 2:
        # fallback: split on blank lines groups
        parts = [p.strip() for p in raw.split("\n\n") if p.strip()]
    out: list[str] = []
    for p in parts[:3]:
        text = p
        if source_url and source_url not in text:
            text = text.rstrip() + "\n\n" + source_url
        out.append(text)
    # ensure at least... caller decides; return what we have
    return out


def separator() -> str:
    return _SEPARATOR