"""Unit tests for the rendering pipeline (no browser, no DB, no network)."""

from __future__ import annotations

import hashlib
from io import BytesIO

from pathlib import Path

from PIL import Image

from app.rendering.models import OfferInput, Viewport
from app.rendering.pipeline import Renderer
from app.rendering.pillow_opt import ImageOptimizer
from app.rendering.screenshot import ScreenshotEngine
from app.rendering.typography import fit_title

TEMPLATE_ID = "emploi"


class RecordingEngine:
    """Fake engine capturing the HTML it was asked to screenshot."""

    def __init__(self) -> None:
        self.html: str | None = None

    def screenshot(self, html: str, viewport: Viewport) -> bytes:
        self.html = html
        image = Image.new("RGB", (viewport.width, viewport.height), color="#FFFFFF")
        buffer = BytesIO()
        image.save(buffer, format="PNG", compress_level=6)
        return buffer.getvalue()


def _make_renderer(engine: ScreenshotEngine) -> Renderer:
    import jinja2

    from app.rendering.templates import TEMPLATES_DIR

    jinja_env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=False,
    )
    return Renderer(
        engine=engine,
        optimizer=ImageOptimizer(),
        jinja_env=jinja_env,
        viewport=Viewport(width=1080, height=1350),
    )


def _offer(**overrides) -> OfferInput:
    data = {
        "title": "Développeur Python",
        "company": "ACME Corp",
        "location": "Abidjan",
        "contract_type": "CDI",
        "logo_url": "https://example.com/logo.png",
    }
    data.update(overrides)
    return OfferInput(**data)


def test_render_produces_valid_png():
    from app.rendering.screenshot import FakeScreenshotEngine

    renderer = _make_renderer(FakeScreenshotEngine())
    result = renderer.render(_offer(), TEMPLATE_ID)

    assert result.size == (1080, 1350)
    assert result.template_id == TEMPLATE_ID
    assert result.png_bytes.startswith(b"\x89PNG\r\n\x1a\n")
    with Image.open(BytesIO(result.png_bytes)) as image:
        assert image.size == (1080, 1350)


def test_render_with_logo_shows_logo_not_badge():
    engine = RecordingEngine()
    renderer = _make_renderer(engine)
    result = renderer.render(_offer(), TEMPLATE_ID)

    assert result.png_bytes  # pipeline ran end to end
    assert engine.html is not None
    assert 'src="https://example.com/logo.png"' in engine.html
    assert "<img" in engine.html
    assert '<div class="badge"' not in engine.html


def test_render_without_logo_shows_initials_badge():
    engine = RecordingEngine()
    renderer = _make_renderer(engine)
    result = renderer.render(_offer(logo_url=None, company="Sarl Export"), TEMPLATE_ID)

    assert result.png_bytes
    assert engine.html is not None
    assert "SE" in engine.html
    assert '<div class="badge">' in engine.html
    assert "<img" not in engine.html


def test_long_title_truncates_and_shrinks_in_html():
    engine = RecordingEngine()
    renderer = _make_renderer(engine)
    long_title = "Développeur " * 25  # way beyond the small-font threshold
    renderer.render(_offer(title=long_title), TEMPLATE_ID)

    assert engine.html is not None
    assert "…" in engine.html
    assert 'font-size: 32px' in engine.html
    rendered_title = engine.html.split("<h1 class=\"title\">")[1].split("</h1>")[0]
    assert rendered_title.endswith("…")
    assert len(rendered_title) <= 90


def test_image_path_is_content_addressed():
    renderer = _make_renderer(RecordingEngine())
    result = renderer.render(_offer(), TEMPLATE_ID)
    digest = hashlib.sha256(result.png_bytes).hexdigest()[:16]
    expected = str(Path("generated_assets") / TEMPLATE_ID / f"{digest}.png")
    assert result.image_path == expected


def test_font_size_helper_used_for_title():
    # The pipeline delegates sizing/truncation to fit_title.
    display, size = fit_title("Développeur Python Full Stack Mobile DevOps Data Engineer " * 4)
    assert size == "32"
    assert display.endswith("…")
