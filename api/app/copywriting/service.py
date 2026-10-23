"""Copywriting variant generation service."""

from __future__ import annotations

from typing import Any

from app.copywriting.prompt import build_prompt, parse_variants
from app.core.llm import LLMProvider, get_llm_provider


def generate_variants(
    offer: Any,
    style_content: str | None = None,
    provider: LLMProvider | None = None,
    n: int = 3,
) -> list[str]:
    if provider is None:
        provider = get_llm_provider()
    source_url = getattr(offer, "origin_url", None) or getattr(offer, "application_url", None)
    prompt = build_prompt(offer, style_content)
    raw = provider.rediger(offer, style=style_content)
    # provider.rediger may ignore prompt; use its output. If it returns str.
    if not isinstance(raw, str):
        raw = str(raw)
    variants = parse_variants(raw, source_url)
    if len(variants) > n:
        variants = variants[:n]
    return variants