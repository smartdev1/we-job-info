"""Deduplication helpers: normalization, fingerprinting and trigram similarity."""

from __future__ import annotations

from typing import Any

import hashlib
import re
import unicodedata

_STOP_WORDS = {
    "de", "du", "des", "le", "la", "les", "un", "une", "et", "a", "à",
    "en", "pour", "sur", "avec", "chez", "the", "of", "and",
}


def normalize(text: str | None) -> str:
    """Lowercase, strip accents, punctuation and stop words."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    tokens = [t for t in text.split() if t and t not in _STOP_WORDS]
    return " ".join(tokens)


def fingerprint(company: str | None, title: str | None, city: str | None) -> str | None:
    """Stable hash of normalized company+title+city.

    Returns None when all inputs normalize to empty, so that two offers with
    no metadata are not falsely flagged as duplicates.
    """
    n_company, n_title, n_city = normalize(company), normalize(title), normalize(city)
    if not (n_company or n_title or n_city):
        return None
    key = "|".join([n_company, n_title, n_city])
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def _trigrams(text: str) -> set[str]:
    t = "  " + text + "  "
    return {t[i : i + 3] for i in range(len(t) - 2)}


def trigram_similarity(a: str | None, b: str | None) -> float:
    """pg_trgm-style similarity between two strings (0..1)."""
    na, nb = normalize(a), normalize(b)
    if not na or not nb:
        return 0.0
    ta, tb = _trigrams(na), _trigrams(nb)
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    union = len(ta | tb)
    return inter / union if union else 0.0


def is_duplicate_fingerprint(fp_a: str, fp_b: str) -> bool:
    return bool(fp_a) and fp_a == fp_b


def is_near_duplicate(title_a: str | None, title_b: str | None, threshold: float = 0.6) -> bool:
    return trigram_similarity(title_a, title_b) >= threshold


def detect_duplicates(items: list[dict[str, Any]]) -> dict[Any, Any]:
    """Group offers by fingerprint and return a mapping id -> doublon_de id.

    The first occurrence of a fingerprint is kept as canonical (no duplicate);
    subsequent occurrences point to the canonical id. Offers with no fingerprint
    (empty metadata) are never flagged. Near-duplicates (trigram) are also
    flagged when similarity exceeds the threshold.
    """
    result: dict[Any, Any] = {}
    # Exact fingerprint grouping
    by_fp: dict[str, list[Any]] = {}
    for it in items:
        fp = fingerprint(it.get("company"), it.get("title"), it.get("city"))
        if fp is None:
            continue
        by_fp.setdefault(fp, []).append(it.get("id"))

    for fp, ids in by_fp.items():
        if len(ids) < 2:
            continue
        canonical = ids[0]
        for dup in ids[1:]:
            result[dup] = canonical

    # Near-duplicate by title (only among items not already flagged)
    remaining = [it for it in items if it.get("id") not in result]
    for i, a in enumerate(remaining):
        for b in remaining[i + 1 :]:
            if is_near_duplicate(a.get("title"), b.get("title")):
                result.setdefault(b.get("id"), a.get("id"))
    return result