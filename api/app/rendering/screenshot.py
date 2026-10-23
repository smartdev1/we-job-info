"""Screenshot engines: Playwright in production, deterministic fake in dev/tests.

The engine is intentionally interchangeable so the renderer stays testable
without a browser installation and without network access.
"""

from __future__ import annotations

import hashlib
import logging
from io import BytesIO
from typing import Protocol

from PIL import Image, ImageDraw

from app.rendering.exceptions import ScreenshotError
from app.rendering.models import Viewport

logger = logging.getLogger(__name__)


class ScreenshotEngine(Protocol):
    """Render an HTML string to PNG bytes."""

    def screenshot(self, html: str, viewport: Viewport) -> bytes:
        """Return a PNG screenshot of ``html`` at ``viewport`` size."""


class PlaywrightScreenshotEngine:
    """Real browser screenshot via Playwright (sync API).

    Playwright is a V0.2-tier dependency of this project: it is not pinned in
    ``pyproject.toml`` yet because the local engine is validated first. The
    import is therefore lazy: instantiating this class works without Playwright
    installed, but calling :meth:`screenshot` raises a clear error until
    ``playwright`` (and a Chromium browser) are available.
    """

    def screenshot(self, html: str, viewport: Viewport) -> bytes:
        try:  # lazy import so the module imports without Playwright installed
            from playwright.sync_api import sync_playwright
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise ScreenshotError(
                "Playwright is not installed. Add 'playwright' to dependencies "
                "and run 'playwright install chromium', or use FakeScreenshotEngine."
            ) from exc

        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(
                    args=[
                        "--no-sandbox",
                        "--disable-gpu",
                        # Disable LCD/subpixel font rendering so rasterization
                        # stays stable across runs on the same machine.
                        "--disable-lcd-text",
                        "--disable-font-subpixel-positioning",
                    ]
                )
                try:
                    context = browser.new_context(
                        viewport={
                            "width": viewport.width,
                            "height": viewport.height,
                        },
                        device_scale_factor=viewport.device_scale_factor,
                        timezone_id="UTC",
                        locale="fr-FR",
                        color_scheme="light",
                    )
                    page = context.new_page()
                    # set_content with a base_url of about:blank keeps relative
                    # assets out of play; templates embed assets as data URIs.
                    page.set_content(html, wait_until="networkidle")
                    return page.screenshot(full_page=False, type="png")
                finally:
                    browser.close()
        except Exception as exc:  # browser launch / screenshot failures
            raise ScreenshotError(f"Playwright screenshot failed: {exc}") from exc


class FakeScreenshotEngine:
    """Deterministic stand-in engine used when Playwright is unavailable.

    Produces a viewport-sized PNG whose pixels derive from a SHA-256 of the
    HTML. Same HTML always yields the same bytes, which keeps the pipeline
    deterministic and testable locally without a browser.
    """

    def screenshot(self, html: str, viewport: Viewport) -> bytes:
        digest = hashlib.sha256(html.encode("utf-8")).hexdigest()[:12]

        image = Image.new("RGB", (viewport.width, viewport.height), color="#FFFFFF")
        draw = ImageDraw.Draw(image)
        draw.text(
            (viewport.width // 2, viewport.height // 2),
            f"RENDER {digest}",
            fill="#111827",
            anchor="mm",
        )
        # Thin border so two different HTML inputs rarely collide visually.
        draw.rectangle(
            [0, 0, viewport.width - 1, viewport.height - 1],
            outline="#d1d5db",
            width=2,
        )

        buffer = BytesIO()
        image.save(buffer, format="PNG", compress_level=6)
        return buffer.getvalue()


def get_screenshot_engine() -> ScreenshotEngine:
    """Return the best available screenshot engine for the current environment.

    Prefers Playwright when installed; falls back to the fake engine and logs
    a warning so the absence is visible in logs.
    """
    try:
        import playwright  # noqa: F401 - availability check only

        return PlaywrightScreenshotEngine()
    except ImportError:
        logger.warning(
            "Playwright not installed: using FakeScreenshotEngine. "
            "Install playwright + Chromium for real screenshots."
        )
        return FakeScreenshotEngine()
