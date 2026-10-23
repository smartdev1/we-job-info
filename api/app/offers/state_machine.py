"""Centralized offer status state machine."""

from __future__ import annotations

TRANSITIONS: dict[str, set[str]] = {
    "nouvelle": {"selectionnee", "rejetee"},
    "selectionnee": {"publiee", "nouvelle"},
    "publiee": {"archivee"},
    "rejetee": {"nouvelle"},
    "archivee": set(),
    "expiree": set(),
}


def is_allowed(current: str, target: str) -> bool:
    return target in TRANSITIONS.get(current, set())


def allowed_targets(current: str) -> set[str]:
    return set(TRANSITIONS.get(current, set()))