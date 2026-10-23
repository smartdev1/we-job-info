"""Data models for the visual rendering pipeline."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Viewport:
    """Target rendering size in CSS pixels."""

    width: int = 1080
    height: int = 1350
    device_scale_factor: int = 1


@dataclass(frozen=True)
class OfferInput:
    """Offer data needed to render a visual.

    All fields are optional except the title; missing values degrade
    gracefully (missing logo becomes an initials badge, etc.).
    """

    title: str
    company: str | None = None
    location: str | None = None
    contract_type: str | None = None
    logo_url: str | None = None


@dataclass(frozen=True)
class RenderResult:
    """Outcome of a successful render."""

    png_bytes: bytes
    image_path: str
    template_id: str
    size: tuple[int, int]
