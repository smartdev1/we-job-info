"""Determinism tests: same input must yield byte-identical PNGs.

The fake screenshot engine is used because Playwright is not installed in
this environment (see pipeline.get_screenshot_engine).
"""

from __future__ import annotations

import importlib.util

import pytest

from app.rendering.models import OfferInput
from app.rendering.pipeline import default_renderer
from app.rendering.screenshot import FakeScreenshotEngine, get_screenshot_engine


_PLAYWRIGHT_INSTALLED = importlib.util.find_spec("playwright") is not None


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


@pytest.mark.skipif(
    _PLAYWRIGHT_INSTALLED,
    reason="Playwright est installé : le fallback vers FakeScreenshotEngine ne s'applique pas",
)
def test_get_screenshot_engine_falls_back_to_fake():
    assert isinstance(get_screenshot_engine(), FakeScreenshotEngine)


def test_same_input_twice_is_byte_identical():
    renderer = default_renderer()
    first = renderer.render(_offer(), "emploi")
    second = renderer.render(_offer(), "emploi")

    assert first.png_bytes == second.png_bytes
    assert first.image_path == second.image_path


def test_different_input_different_output():
    renderer = default_renderer()
    first = renderer.render(_offer(), "emploi")
    second = renderer.render(_offer(title="Développeur Java"), "emploi")

    assert first.png_bytes != second.png_bytes


def test_different_template_different_output():
    renderer = default_renderer()
    first = renderer.render(_offer(), "emploi")
    second = renderer.render(_offer(), "stage")

    assert first.png_bytes != second.png_bytes
