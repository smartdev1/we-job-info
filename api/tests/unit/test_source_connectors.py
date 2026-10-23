"""Connector tests against real captured markup.

The fixtures under tests/fixtures/sources/ are trimmed captures of the live
listing pages, not hand-written idealisations. A hand-written fixture used to
stay green while the real site kept returning something else entirely.
"""

from pathlib import Path

import pytest

from app.sources.base import Offer, is_themed, match_theme
from app.sources.eclozion import EclozionConnector
from app.sources.educarriere import EducarriereConnector
from app.sources.emploi_ci import EmploiCiConnector
from app.sources.emploiivoire import EmploiIvoireConnector
from app.sources.jobivoire import JobIvoireConnector

FIX = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "sources"

CONNECTORS = [
    ("emploi_ci", EmploiCiConnector),
    ("educarriere", EducarriereConnector),
    ("eclozion", EclozionConnector),
    ("emploiivoire", EmploiIvoireConnector),
    ("jobivoire", JobIvoireConnector),
]


def _read(name: str) -> str:
    return (FIX / f"{name}.html").read_text(encoding="utf-8")


@pytest.mark.parametrize(("name", "connector_cls"), CONNECTORS)
def test_every_connector_finds_jobs_in_the_real_markup(name, connector_cls):
    html = _read(name)
    connector = connector_cls(fetcher=lambda url: html)
    candidates = connector.parse_candidates(html)
    assert candidates, f"{name} found no job in the captured listing"
    assert all(isinstance(o, Offer) for o in candidates)


@pytest.mark.parametrize(("name", "connector_cls"), CONNECTORS)
def test_titles_never_contain_the_card_description(name, connector_cls):
    """A title is the job title, never the whole card or its body text."""
    html = _read(name)
    connector = connector_cls(fetcher=lambda url: html)
    for offer in connector.parse_candidates(html):
        assert len(offer.title) <= 200
        assert "Description du poste" not in offer.title
        assert "Entreprise :" not in offer.title
        assert "Type de contrat" not in offer.title


def test_emploiivoire_title_comes_from_the_h3():
    html = _read("emploiivoire")
    connector = EmploiIvoireConnector(fetcher=lambda url: html)
    titles = [o.title for o in connector.parse_candidates(html)]
    assert "Agent commercial Mandataire" in titles
    # The card also carries the level badge and the full description; none of
    # it may leak into the title.
    assert all(not t.startswith("<") for t in titles)
    assert all("BEPC" not in t for t in titles)


def test_jobivoire_title_comes_from_the_screen_reader_span():
    html = _read("jobivoire")
    connector = JobIvoireConnector(fetcher=lambda url: html)
    titles = [o.title for o in connector.parse_candidates(html)]
    assert "Volailler" in titles
    assert "Business Analyst" in titles
    # The "Voir l'offre" button text is not part of the title.
    assert all(not t.startswith("Voir l'offre") for t in titles)
    assert all(t != "Voir l'offre" for t in titles)


def test_educarriere_title_comes_from_the_bold_div():
    html = _read("educarriere")
    connector = EducarriereConnector(fetcher=lambda url: html)
    titles = [o.title for o in connector.parse_candidates(html)]
    assert "INGENIEUR SECURITE FERROVIAIRE (H/F)" in titles
    # The company name and the deadline live in sibling divs.
    assert all("Limite" not in t for t in titles)
    assert all("ENTREPRISE" not in t for t in titles)


def test_eclozion_skips_the_thumbnail_anchor():
    html = _read("eclozion")
    connector = EclozionConnector(fetcher=lambda url: html)
    titles = [o.title for o in connector.parse_candidates(html)]
    assert "Chef Comptable" in titles
    assert all(not t.startswith("<figure") for t in titles)


def test_theme_filter_uses_the_title_not_the_description():
    """A job whose description mentions tech but whose title does not is out."""
    card = """
    <a href="https://emploiivoire.ci/post/1">
      <h3>Vendeur deBIT</h3>
      <p>Entreprise : X Lieu : Abidjan Description du poste : vous developpez
      des applications web et analysez de la data avec python et react</p>
    </a>
    """
    connector = EmploiIvoireConnector(fetcher=lambda url: card)
    assert connector.parse_candidates(card)[0].title == "Vendeur deBIT"
    assert connector.parse_listing(card) == []


def test_theme_filter_keeps_a_tech_title():
    card = """
    <a href="https://emploiivoire.ci/post/2">
      <h3>Developpeur Python</h3>
      <p>Entreprise : X Lieu : Abidjan</p>
    </a>
    """
    connector = EmploiIvoireConnector(fetcher=lambda url: card)
    assert [o.title for o in connector.parse_listing(card)] == ["Developpeur Python"]


def test_sante_separates_candidates_from_themed_items():
    html = _read("jobivoire")
    connector = JobIvoireConnector(fetcher=lambda url: html)
    health = connector.sante()
    assert health["status"] == "ok"
    assert health["candidates"] == 12
    # The captured jobivoire listing holds no tech job, which is a fact about
    # the site, not a parsing failure.
    assert health["items"] == 0


def test_lister_returns_only_themed_offers():
    html = _read("educarriere")
    connector = EducarriereConnector(fetcher=lambda url: html)
    offers = connector.lister()
    assert all(is_themed(o.title) for o in offers)
    assert any("SECURITE" in o.title for o in offers)


def test_recuperer_returns_content():
    connector = EducarriereConnector(fetcher=lambda url: "<html>detail</html>")
    out = connector.recuperer("https://example.com/x")
    assert "detail" in out


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Developpeur Python", "developpeur"),
        ("Développeurs Fullstack", "développeur"),
        ("Data Analyst Senior", "data"),
        ("Ingénieur Sécurité des Systèmes d'Information", "sécurité"),
        ("Assistant IA - Abidjan", "ia"),
    ],
)
def test_match_theme_accepts_real_titles(title, expected):
    assert match_theme(title) == expected


@pytest.mark.parametrize(
    "title",
    [
        "Agent commercial Mandataire",
        "Analyste Risque de Crédit Senior",
        "Ingénieur Conception Mécanique",
        "Responsable Spa",
        "Société Ivoirienne de Banque",
        "Chef Comptable",
    ],
)
def test_match_theme_rejects_off_theme_titles(title):
    assert match_theme(title) is None


def test_short_keywords_do_not_match_inside_words():
    """'soc' must not match 'société' and 'ia' must not match 'recherche'."""
    assert match_theme("Chargé de la recherche scientifique") is None
    assert match_theme("Secrétaire de société") is None
    # But the standalone token still matches.
    assert match_theme("Analyste SOC (H/F)") == "soc"
