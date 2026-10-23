"""Visual rendering pipeline: Jinja2 template -> screenshot -> Pillow PNG."""

from __future__ import annotations

from app.rendering.exceptions import (
    OptimizationError,
    RenderingError,
    ScreenshotError,
    TemplateError,
)
from app.rendering.models import OfferInput, RenderResult, Viewport
from app.rendering.pipeline import Renderer, default_renderer, render_offer
from app.rendering.screenshot import (
    FakeScreenshotEngine,
    PlaywrightScreenshotEngine,
    get_screenshot_engine,
)
from app.rendering.typography import badge_color, fit_title, initials

__all__ = [
    "FakeScreenshotEngine",
    "OfferInput",
    "OptimizationError",
    "PlaywrightScreenshotEngine",
    "Renderer",
    "RenderResult",
    "ScreenshotError",
    "TemplateError",
    "Viewport",
    "badge_color",
    "default_renderer",
    "fit_title",
    "get_screenshot_engine",
    "initials",
    "render_offer",
]
