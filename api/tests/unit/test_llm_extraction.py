"""Unit tests for structured LLM extraction (core/llm.py)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from app.core.llm import ExtractionError, KiloLLMProvider
from app.extraction import OffreExtraite


def _provider() -> KiloLLMProvider:
    with patch("app.core.llm.get_settings") as gs:
        s = MagicMock()
        s.kilo_api_url = "http://x"
        s.kilo_api_key = "key"
        s.kilo_model = "m"
        s.llm_model_extraction = "m"
        s.llm_provider = "kilo"
        gs.return_value = s
        return KiloLLMProvider()


def test_parse_valid_json():
    p = _provider()
    raw = json.dumps({"title": "Dev", "company": "ACME", "confiance": {"title": "high"}})
    o = p._parse(raw)
    assert isinstance(o, OffreExtraite)
    assert o.title == "Dev"
    assert o.company == "ACME"


def test_parse_invalid_json_raises():
    p = _provider()
    with pytest.raises((json.JSONDecodeError, ValueError)):
        p._parse("not json at all")


def test_parse_extracts_json_from_surrounding_text():
    p = _provider()
    raw = 'Here is the result: {"title": "Dev", "company": "ACME"} thanks!'
    o = p._parse(raw)
    assert o.title == "Dev"
    assert o.company == "ACME"


def test_parse_invalid_schema_raises_validation_error():
    p = _provider()
    raw = json.dumps({"confiance": {"title": "super"}})
    with pytest.raises(ValidationError):
        p._parse(raw)


def test_extraire_retries_once_then_raises(monkeypatch):
    p = _provider()
    client = MagicMock()
    p._client = lambda: client  # type: ignore
    bad = MagicMock()
    bad.choices = [MagicMock(message=MagicMock(content="not json"))]
    client.chat.completions.create.return_value = bad

    with pytest.raises(ExtractionError):
        p.extraire("content")
    assert client.chat.completions.create.call_count == 2


def test_extraire_success_first_attempt(monkeypatch):
    p = _provider()
    client = MagicMock()
    p._client = lambda: client  # type: ignore
    good = MagicMock()
    good.choices = [MagicMock(message=MagicMock(content=json.dumps({"title": "Dev"})))]
    client.chat.completions.create.return_value = good

    o = p.extraire("content")
    assert o.title == "Dev"
    assert client.chat.completions.create.call_count == 1


def test_parse_fills_confiance_when_missing():
    p = _provider()
    raw = json.dumps({"title": "Dev", "company": None})
    o = p._parse(raw)
    assert o.confiance["title"] == "high"
    assert o.confiance["company"] == "low"


def test_parse_keeps_provided_confiance():
    p = _provider()
    raw = json.dumps({"title": "Dev", "confiance": {"title": "medium"}})
    o = p._parse(raw)
    assert o.confiance["title"] == "medium"
    # missing fields still filled
    assert o.confiance["company"] == "low"


def test_parse_ambiguous_email_medium():
    p = _provider()
    raw = json.dumps({"contact_email": "not-an-email"})
    o = p._parse(raw)
    assert o.confiance["contact_email"] == "medium"
