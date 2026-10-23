from app.copywriting.prompt import parse_variants


def test_parse_variants_adds_source_link() -> None:
    raw = "Variant one text\n---VARIANT---\nVariant two text"
    out = parse_variants(raw, "https://example.com/offer")
    assert len(out) == 2
    assert all("https://example.com/offer" in v for v in out)


def test_parse_variants_keeps_existing_link() -> None:
    raw = "See https://example.com/offer\n---VARIANT---\nAlso https://example.com/offer"
    out = parse_variants(raw, "https://example.com/offer")
    assert len(out) == 2