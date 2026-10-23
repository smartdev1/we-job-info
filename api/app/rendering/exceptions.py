"""Errors raised by the rendering pipeline."""

from __future__ import annotations


class RenderingError(Exception):
    """Base error for rendering failures."""


class TemplateError(RenderingError):
    """Raised when a template cannot be loaded or rendered."""


class ScreenshotError(RenderingError):
    """Raised when the browser screenshot fails."""


class OptimizationError(RenderingError):
    """Raised when image optimization fails."""
