"""Unit tests for OffreExtraite schema and confidence scoring (T-008)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.extraction import ConfidenceLevel, OffreExtraite


def test_all_fields_nullable_by_default():
    o = OffreExtraite()
    assert o.title is None
    assert o.company is None
    assert o.deadline is None
    assert o.missions is None
    assert o.confiance == {}


def test_is_job_posting_defaults_true():
    o = OffreExtraite()
    assert o.is_job_posting is True
    assert o.is_not_a_job_posting() is False


def test_not_a_job_posting_classification():
    o = OffreExtraite(is_job_posting=False, not_a_job_reason="newsletter")
    assert o.is_not_a_job_posting() is True
    assert o.not_a_job_reason == "newsletter"


def test_confiance_valid_levels():
    o = OffreExtraite(confiance={"title": "high", "company": "medium"})
    assert o.confiance["title"] == "high"


def test_confiance_invalid_level_rejected():
    with pytest.raises(ValidationError):
        OffreExtraite(confiance={"title": "super"})


def test_missing_field_stored_as_none_not_invented():
    o = OffreExtraite(title="Engineer")
    assert o.company is None
    assert o.location is None


def test_exports_available():
    import app.extraction as pkg

    assert "OffreExtraite" in pkg.__all__
    assert "ConfidenceLevel" in pkg.__all__
    assert ConfidenceLevel.high.value == "high"
    assert {c.value for c in ConfidenceLevel} == {"high", "medium", "low"}
