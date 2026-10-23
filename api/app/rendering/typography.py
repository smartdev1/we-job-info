"""Pure typography helpers for the rendering pipeline.

All functions here are deterministic: same input always yields same output.
No randomness, no clock, no network.
"""

from __future__ import annotations

import hashlib

# Portrait format 1080x1350 (CSS pixels). Title area width is ~900px after
# padding; these thresholds map title length to a font size that keeps the
# title on a single line. Values are starting points to calibrate empirically.
LARGE_FONT_SIZE_PX = 60
MEDIUM_FONT_SIZE_PX = 44
SMALL_FONT_SIZE_PX = 32

LARGE_MAX_CHARS = 42
MEDIUM_MAX_CHARS = 64
SMALL_MAX_CHARS = 90

DEFAULT_FONT_SIZE_PX = str(LARGE_FONT_SIZE_PX)

# Badge background colors used when no company logo is available. Picked from
# an accessible, muted palette; the choice is deterministic per company name.
BADGE_PALETTE: list[str] = [
    "#374151",
    "#7c3aed",
    "#be185d",
    "#0891b2",
    "#15803d",
    "#b45309",
    "#4f46e5",
    "#db2777",
]


def fit_title(title: str) -> tuple[str, str]:
    """Adapt font size to title length, then truncate with ellipsis.

    Returns ``(display_title, font_size_px)``.

    Order matters: we first reduce the font size so longer titles still fit,
    and only truncate with an ellipsis when the title remains too long even
    at the smallest size. Truncation happens on a word boundary when possible
    to avoid cutting words in half.
    """
    title = (title or "").strip()
    if not title:
        return "", DEFAULT_FONT_SIZE_PX

    if len(title) <= LARGE_MAX_CHARS:
        return title, str(LARGE_FONT_SIZE_PX)
    if len(title) <= MEDIUM_MAX_CHARS:
        return title, str(MEDIUM_FONT_SIZE_PX)
    if len(title) <= SMALL_MAX_CHARS:
        return title, str(SMALL_FONT_SIZE_PX)

    return _truncate(title, SMALL_MAX_CHARS), str(SMALL_FONT_SIZE_PX)


def _truncate(text: str, max_chars: int) -> str:
    """Truncate ``text`` to at most ``max_chars`` including the ellipsis."""
    budget = max_chars - 1  # room for the ellipsis character
    cut = text[:budget]
    space = cut.rfind(" ")
    if 0.5 * max_chars < space < budget:
        cut = cut[:space]
    return cut.rstrip() + "…"


def initials(company: str | None) -> str:
    """Return up to two uppercase initials from a company name.

    Falls back to ``"??"`` when no company is known.
    """
    if not company:
        return "??"
    parts = [part for part in company.split() if part]
    if not parts:
        return "??"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def badge_color(company: str | None) -> str:
    """Deterministic badge background color derived from the company name.

    Same company always yields the same color; unknown companies get the
    first (neutral) palette entry.
    """
    if not company:
        return BADGE_PALETTE[0]
    digest = int(hashlib.sha256(company.encode("utf-8")).hexdigest(), 16)
    return BADGE_PALETTE[digest % len(BADGE_PALETTE)]
