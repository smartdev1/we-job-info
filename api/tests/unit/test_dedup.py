from app.services.dedup import (
    normalize,
    fingerprint,
    trigram_similarity,
    is_duplicate_fingerprint,
    is_near_duplicate,
    detect_duplicates,
)


def test_fingerprint_none_when_empty():
    assert fingerprint(None, None, None) is None
    assert fingerprint("", "  ", None) is None


def test_detect_duplicates_groups():
    items = [
        {"id": 1, "company": "ACME", "title": "Dev", "city": "Abidjan"},
        {"id": 2, "company": "acme", "title": "dev", "city": "abidjan"},
        {"id": 3, "company": "Other", "title": "Comptable", "city": "Yamoussoukro"},
    ]
    result = detect_duplicates(items)
    assert result.get(2) == 1
    assert 3 not in result


def test_detect_duplicates_empty_not_flagged():
    items = [
        {"id": 1, "company": None, "title": None, "city": None},
        {"id": 2, "company": None, "title": None, "city": None},
    ]
    assert detect_duplicates(items) == {}


def test_normalize_strips_accents_and_stopwords():
    assert normalize("Développeur Web à Abidjan") == "developpeur web abidjan"


def test_fingerprint_matches_identical():
    fp1 = fingerprint("ACME", "Dev Web", "Abidjan")
    fp2 = fingerprint("acme", "dev web", "abidjan")
    assert fp1 == fp2


def test_fingerprint_differs_on_city():
    assert fingerprint("ACME", "Dev Web", "Abidjan") != fingerprint("ACME", "Dev Web", "Bouake")


def test_trigram_similarity_identical():
    assert trigram_similarity("développeur web", "développeur web") == 1.0


def test_near_duplicate_flags_similar():
    assert is_near_duplicate("Développeur web Python", "Developpeur web python senior")


def test_is_duplicate_fingerprint():
    assert is_duplicate_fingerprint("abc", "abc")
    assert not is_duplicate_fingerprint("abc", "def")
    assert not is_duplicate_fingerprint("", "abc")


def test_fingerprint_all_none():
    assert fingerprint(None, None, None) is None


def test_trigram_similarity_none():
    assert trigram_similarity(None, "x") == 0.0
    assert trigram_similarity("x", None) == 0.0


def test_normalize_punctuation_only():
    assert normalize("!!!") == ""