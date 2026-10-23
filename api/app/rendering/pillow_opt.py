"""Pillow-based PNG optimization.

The output is deterministic: same input bytes always produce the same output
bytes (no timestamps, no metadata, fixed compression level).
"""

from __future__ import annotations

from io import BytesIO

from PIL import Image

from app.rendering.exceptions import OptimizationError

DEFAULT_COMPRESS_LEVEL = 6


class ImageOptimizer:
    """Re-encode a PNG so the final asset is normalized and compact."""

    def __init__(self, compress_level: int = DEFAULT_COMPRESS_LEVEL) -> None:
        if not 0 <= compress_level <= 9:
            raise ValueError("compress_level must be between 0 and 9")
        self.compress_level = compress_level

    def optimize(self, png_bytes: bytes) -> bytes:
        """Decode, normalize, and re-encode ``png_bytes`` deterministically."""
        try:
            with Image.open(BytesIO(png_bytes)) as image:
                image.load()
                # Drop any alpha channel (backgrounds are opaque JPEG) and all
                # metadata; Pillow writes no creation timestamp into PNG.
                normalized = image.convert("RGB")
                buffer = BytesIO()
                normalized.save(
                    buffer,
                    format="PNG",
                    compress_level=self.compress_level,
                )
                return buffer.getvalue()
        except Exception as exc:  # corrupt image, unsupported format, etc.
            raise OptimizationError(f"PNG optimization failed: {exc}") from exc
