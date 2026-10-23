"""End-to-end rendering pipeline: Jinja2 template -> screenshot -> Pillow PNG.

Usage::

    from app.rendering import render_offer

    result = render_offer(
        OfferInput(title="Dev Python", company="ACME", location="Abidjan"),
        template_id="emploi",
    )
    # result.png_bytes is the final PNG; result.image_path is the suggested
    # GeneratedAsset.image_path value for the caller to persist.
"""

from __future__ import annotations

import base64
import hashlib
import logging
from pathlib import Path
from urllib.parse import urlparse

import jinja2

from app.rendering.exceptions import RenderingError, TemplateError
from app.rendering.models import OfferInput, RenderResult, Viewport
from app.rendering.pillow_opt import DEFAULT_COMPRESS_LEVEL, ImageOptimizer
from app.rendering.screenshot import (
    FakeScreenshotEngine,
    ScreenshotEngine,
    get_screenshot_engine,
)
from app.rendering.templates import get_template
from app.rendering.typography import badge_color, fit_title, initials

# SchÃ©mas d'URL autorisÃ©s pour logo_url (fournis par l'utilisateur via l'API).
# data: est refusÃ© cÃ´tÃ© logo (mÃªme si background l'utilise en interne, de faÃ§on fiable).
ALLOWED_LOGO_URL_SCHEMES = {"http", "https"}

logger = logging.getLogger(__name__)

def _validate_logo_url(logo_url: str | None) -> str | None:
    """Rejette logo_url si le schÃ©ma d'URL n'est pas http/https.

    EmpÃªche une injection javascript: ou data: via le champ logo_url
    transmis par l'appelant de l'API /recognize.
    """
    if not logo_url:
        return None
    parsed = urlparse(logo_url)
    if parsed.scheme not in ALLOWED_LOGO_URL_SCHEMES:
        raise TemplateError(
            f"logo_url scheme non autorisÃ©: {parsed.scheme or '(aucun)'}"
        )
    try:
        from app.services.url_safety import _resolve_and_check
        _resolve_and_check(parsed.hostname or "")
    except Exception as exc:
        raise TemplateError(f"logo_url non autorisée: {exc}") from exc
    return logo_url


DEFAULT_VIEWPORT = Viewport()
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
DEFAULT_IMAGE_DIR = Path("generated_assets")


class Renderer:
    """Render an offer to a deterministic PNG asset.

    Dependencies are injected so every piece can be tested without a browser,
    filesystem writes, or the clock.
    """

    def __init__(
        self,
        engine: ScreenshotEngine,
        optimizer: ImageOptimizer,
        jinja_env: jinja2.Environment,
        viewport: Viewport = DEFAULT_VIEWPORT,
    ) -> None:
        self.engine = engine
        self.optimizer = optimizer
        self.jinja_env = jinja_env
        self.viewport = viewport

    def render(self, offer: OfferInput, template_id: str) -> RenderResult:
        """Render ``offer`` with ``template_id`` and return the PNG result."""
        try:
            template = get_template(template_id)
        except KeyError as exc:
            raise TemplateError(str(exc)) from exc

        background_uri = _data_uri(template.background)
        display_title, font_size = fit_title(offer.title)
        initials_text = initials(offer.company)
        color = badge_color(offer.company)
        safe_logo_url = _validate_logo_url(offer.logo_url)

        html = self.jinja_env.get_template("offre.html.j2").render(
            title=display_title,
            font_size=font_size,
            company=offer.company or "",
            location=offer.location or "",
            contract_type=offer.contract_type or "",
            logo_url=safe_logo_url or "",
            has_logo=bool(safe_logo_url),
            initials=initials_text,
            badge_color=color,
            background=background_uri,
        )

        screenshot_png = self.engine.screenshot(html, self.viewport)
        png_bytes = self.optimizer.optimize(screenshot_png)

        # Content-addressed path: same bytes always yield the same path,
        # keeping RenderResult fully deterministic.
        digest = hashlib.sha256(png_bytes).hexdigest()[:16]
        image_path = str(DEFAULT_IMAGE_DIR / template_id / f"{digest}.png")

        return RenderResult(
            png_bytes=png_bytes,
            image_path=image_path,
            template_id=template_id,
            size=(self.viewport.width, self.viewport.height),
        )


def _data_uri(path: Path) -> str:
    """Embed a local image as a data URI (no network access at render time)."""
    data = path.read_bytes()
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def default_renderer() -> Renderer:
    """Build a renderer with the best available engine for this environment."""
    jinja_env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=False,  # user text is escaped explicitly with the 'e' filter
    )
    return Renderer(
        engine=get_screenshot_engine(),
        optimizer=ImageOptimizer(compress_level=DEFAULT_COMPRESS_LEVEL),
        jinja_env=jinja_env,
    )


def render_offer(offer: OfferInput, template_id: str) -> RenderResult:
    """Convenience rendering with the default environment engine."""
    return default_renderer().render(offer, template_id)
