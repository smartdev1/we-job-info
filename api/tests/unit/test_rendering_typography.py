"""Unit tests for rendering typography helpers (pure, deterministic)."""

from app.rendering.typography import badge_color, fit_title, initials


def test_fit_title_short_keeps_big_font():
    title, size = fit_title("Dev Python")
    assert title == "Dev Python"
    assert size == "60"


def test_fit_title_exact_threshold():
    title = "A" * 42
    assert fit_title(title) == (title, "60")


def test_fit_title_medium_reduces_font():
    title = "A" * 50
    display, size = fit_title(title)
    assert display == title
    assert size == "44"


def test_fit_title_long_reduces_font():
    title = "A" * 75
    display, size = fit_title(title)
    assert display == title
    assert size == "32"


def test_fit_title_very_long_truncates_with_ellipsis():
    title = "Développeur Python Full Stack Mobile DevOps Data Engineer " * 4
    display, size = fit_title(title)
    assert size == "32"
    assert display.endswith("…")
    assert len(display) <= 90
    assert len(display) < len(title)


def test_fit_title_empty():
    assert fit_title("") == ("", "60")
    assert fit_title("   ") == ("", "60")


def test_initials_two_words():
    assert initials("ACME Corp") == "AC"


def test_initials_single_word():
    assert initials("Apple") == "AP"


def test_initials_missing_company():
    assert initials(None) == "??"
    assert initials("") == "??"
    assert initials("   ") == "??"


def test_badge_color_deterministic():
    assert badge_color("ACME") == badge_color("ACME")
    assert badge_color(None) == badge_color("")

