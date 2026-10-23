"""LLM abstraction layer.

Single integration point for all LLM calls (extraction, copywriting).
Provider selection is driven by the LLM_PROVIDER env var so swapping
providers is a configuration change, not a code change.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any

from app.core.config import get_settings
from app.extraction import OffreExtraite


class LLMError(Exception):
    """Base exception for LLM failures."""


class ExtractionError(LLMError):
    """Raised when structured extraction fails to produce a valid OffreExtraite."""


class LLMProvider(ABC):
    """Common contract honored by every provider."""

    @abstractmethod
    def extraire(self, contenu: Any) -> OffreExtraite:
        """Extract structured offer data from cleaned content."""

    @abstractmethod
    def rediger(self, offre: Any, style: str | None = None) -> Any:
        """Draft copywriting variants for an offer."""


class KiloLLMProvider(LLMProvider):
    """Kilo AI provider via an OpenAI-compatible client."""

    def __init__(self) -> None:
        settings = get_settings()
        self._api_url = settings.kilo_api_url
        self._api_key = settings.kilo_api_key
        self._model = settings.kilo_model or settings.llm_model_extraction

    def _client(self) -> Any:
        from openai import OpenAI

        return OpenAI(base_url=self._api_url, api_key=self._api_key)

    def _extraction_prompt(self, contenu: Any) -> str:
        schema = OffreExtraite.model_json_schema()
        return (
            "You extract a job offer from the provided content and return ONLY a "
            "valid JSON object matching the following schema. Do not invent data: "
            "use null for any field that is not present in the content. "
            "For every field, provide a confidence level in the 'confiance' object "
            "(field name -> 'high', 'medium' or 'low'). Use 'high' when the value "
            "is clearly present and unambiguous, 'medium' when present but "
            "ambiguous or partially inferred, and 'low' (or omit) when absent. "
            "Your entire response must be a single valid JSON object, with no "
            "markdown, no code fences, and no explanatory text before or after.\n\n"
            f"Schema:\n{json.dumps(schema, ensure_ascii=False)}\n\n"
            f"Content:\n{contenu}"
        )

    @staticmethod
    def _extract_json(raw: str) -> str:
        raw = raw.strip()
        try:
            json.loads(raw)
            return raw
        except json.JSONDecodeError:
            pass
        # Fallback: pull the first JSON object out of surrounding text.
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = raw[start : end + 1]
            json.loads(candidate)  # validate
            return candidate
        raise json.JSONDecodeError("no JSON object found", raw, 0)

    # Fields whose values are evaluated by the heuristic below.
    _CORE_FIELDS = (
        "title", "company", "location", "city", "country", "contract_type",
        "education", "experience", "sector", "description", "missions", "profile",
        "benefits", "how_to_apply", "contact_email", "application_url",
        "deadline", "is_job_posting", "not_a_job_reason",
    )

    @staticmethod
    def _heuristic_confidence(field: str, value: Any) -> str:
        if value is None:
            return "low"
        if isinstance(value, list) and not value:
            return "low"
        if isinstance(value, str) and not value.strip():
            return "low"
        if field == "contact_email":
            return "high" if isinstance(value, str) and "@" in value else "medium"
        if field == "application_url":
            return "high" if isinstance(value, str) and value.startswith(("http://", "https://")) else "medium"
        if field == "deadline":
            # Already parsed into a datetime by Pydantic -> high; a raw
            # unparseable string never reaches here (validation would fail).
            return "high"
        return "high"

    @classmethod
    def _fill_confiance(cls, offre: OffreExtraite) -> OffreExtraite:
        confiance = dict(offre.confiance or {})
        for field in cls._CORE_FIELDS:
            if field not in confiance:
                confiance[field] = cls._heuristic_confidence(field, getattr(offre, field, None))
        offre.confiance = confiance
        return offre

    def _parse(self, raw: str) -> OffreExtraite:
        data = json.loads(self._extract_json(raw))
        offre = OffreExtraite.model_validate(data)
        return self._fill_confiance(offre)

    def extraire(self, contenu: Any) -> OffreExtraite:
        client = self._client()
        messages = [{"role": "user", "content": self._extraction_prompt(contenu)}]

        last_error: Exception | None = None
        for _attempt in range(2):
            response = client.chat.completions.create(
                model=self._model,
                messages=messages,
            )
            raw = response.choices[0].message.content
            try:
                return self._parse(raw)
            except (json.JSONDecodeError, ValueError) as exc:
                last_error = exc
                # Retry once with the validation error fed back to the model.
                messages = [
                    {"role": "user", "content": self._extraction_prompt(contenu)},
                    {"role": "assistant", "content": raw},
                    {
                        "role": "user",
                        "content": (
                            "The previous JSON did not validate against the schema: "
                            f"{exc}. Return a corrected JSON object only."
                        ),
                    },
                ]
        raise ExtractionError(f"structured extraction failed: {last_error}")

    def rediger(self, offre: Any, style: str | None = None) -> Any:
        try:
            from app.copywriting.prompt import build_prompt

            prompt = build_prompt(offre, style)
        except Exception:
            prompt = str(offre)
        client = self._client()
        response = client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content


def get_llm_provider() -> LLMProvider:
    """Factory selecting the provider from settings."""
    settings = get_settings()
    if settings.llm_provider == "kilo":
        return KiloLLMProvider()
    if settings.llm_provider == "anthropic":
        raise NotImplementedError("Anthropic provider not implemented yet")
    raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")