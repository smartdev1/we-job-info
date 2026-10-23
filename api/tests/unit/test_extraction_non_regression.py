"""Non-regression harness for offer extraction.

Replays every fixture pair in tests/fixtures/offers/ and asserts that at
least 90% of the key fields (title, company, location, contract_type,
deadline, how_to_apply) are extracted correctly.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "offers"
KEY_FIELDS = ["title", "company", "location", "contract_type", "deadline", "how_to_apply"]


def _load_fixtures():
    pairs = []
    for txt in sorted(FIXTURE_DIR.glob("*.txt")):
        expected_path = txt.with_suffix(".expected.json")
        # expected file naming: offer_XX.expected.json
        expected_path = txt.parent / (txt.stem + ".expected.json")
        if expected_path.exists():
            pairs.append((txt, expected_path))
    return pairs


def _get_extractor():
    try:
        from app.extraction import extract_offer  # type: ignore[attr-defined]
    except Exception:  # pragma: no cover - pending implementation
        return None
    return extract_offer


@pytest.mark.skipif(_get_extractor() is None, reason="extraction module not implemented yet")
def test_extraction_non_regression_aggregate():
    extractor = _get_extractor()
    pairs = _load_fixtures()
    assert pairs, "no fixtures found"
    correct_total = 0
    field_total = 0
    per_fixture = []
    for txt_path, expected_path in pairs:
        text = txt_path.read_text(encoding="utf-8")
        expected = json.loads(expected_path.read_text(encoding="utf-8"))
        result = extractor(text)
        result_dict = result if isinstance(result, dict) else getattr(result, "__dict__", {})
        correct = sum(1 for f in KEY_FIELDS if result_dict.get(f) == expected.get(f))
        correct_total += correct
        field_total += len(KEY_FIELDS)
        per_fixture.append((txt_path.name, correct, len(KEY_FIELDS)))
    ratio = correct_total / field_total
    assert ratio >= 0.9, f"aggregate {correct_total}/{field_total} = {ratio:.3f} < 0.9; {per_fixture}"
