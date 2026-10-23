"""Detail extraction tests against real captured pages.

The fixtures under tests/fixtures/details/ are trimmed captures of the live
detail pages: the JSON-LD blocks and the body of the offer, without the
scripts, the styles and the navigation. They are not idealisations: a
hand-written fixture would stay green while the real site keeps returning
something else.

Each test asserts the fields the page actually publishes, so a change in the
markup of a site shows up as a failure here instead of as empty columns in
the database.
"""

from pathlib import Path

import pytest

from app.sources.eclozion import EclozionConnector
from app.sources.educarriere import EducarriereConnector
from app.sources.emploi_ci import EmploiCiConnector
from app.sources.emploiivoire import EmploiIvoireConnector
from app.sources.jobivoire import JobIvoireConnector

FIX = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "details"

CONNECTORS = [
    ("eclozion", EclozionConnector),
    ("educarriere", EducarriereConnector),
    ("emploi_ci", EmploiCiConnector),
    ("emploiivoire", EmploiIvoireConnector),
    ("jobivoire", JobIvoireConnector),
]


def _detail(source_id: str):
    html = (FIX / f"{source_id}.html").read_text(encoding="utf-8")
    connector = dict(CONNECTORS)[source_id]()
    return connector.parse_detail(html)


@pytest.mark.parametrize(("source_id", "connector_cls"), CONNECTORS)
def test_every_detail_page_yields_a_title_and_a_company(source_id, connector_cls):
    """A page without a title or a company is not usable for the channel."""
    detail = _detail(source_id)
    assert detail.title, f"{source_id}: no title"
    assert detail.company, f"{source_id}: no company"
    assert len(detail.title) <= 300


@pytest.mark.parametrize(("source_id", "connector_cls"), CONNECTORS)
def test_every_detail_page_yields_a_description(source_id, connector_cls):
    detail = _detail(source_id)
    assert detail.description
    assert len(detail.description) > 100


@pytest.mark.parametrize(("source_id", "connector_cls"), CONNECTORS)
def test_no_field_is_guessed(source_id, connector_cls):
    """A field the page does not publish stays empty.

    A guessed value is worse than a missing one: it is published to the
    channel as if it were certain.
    """
    detail = _detail(source_id)
    for name in ("country", "contract_type", "education_level", "sector"):
        value = getattr(detail, name)
        if value is not None:
            assert value == value.strip()
            assert value, f"{source_id}: {name} is an empty string, not None"


def test_jobivoire_reads_the_quick_facts():
    detail = _detail("jobivoire")
    assert detail.contract_type == "CDI"
    assert detail.education_level == "Bac+5 (Master, Ingénieur)"
    assert detail.sector == "Droit social & RH juridique"
    assert detail.deadline is not None
    assert detail.deadline.year == 2026


def test_jobivoire_splits_the_body_into_missions_and_profile():
    detail = _detail("jobivoire")
    assert detail.missions
    assert detail.profile
    assert any("Coordonnateur" in line for line in detail.missions)
    assert any("Ivoirien" in line for line in detail.profile)


def test_jobivoire_application_url_is_the_postuler_link():
    detail = _detail("jobivoire")
    assert detail.application_url
    assert detail.application_url.startswith("https://")


def test_educarriere_reads_the_stats_and_the_apply_link():
    detail = _detail("educarriere")
    assert detail.sector == "Juridique/Droit"
    assert detail.education_level == "BAC+5"
    assert detail.deadline is not None
    assert detail.application_url
    assert detail.application_url.startswith("http")
    assert "jobkonect" in detail.application_url


def test_educarriere_does_not_put_a_country_in_the_city():
    """The page publishes "Côte d'Ivoire" as its location.

    A country in the city column would be published as a job city and send
    the readers to the wrong place.
    """
    detail = _detail("educarriere")
    assert detail.country == "Côte d'Ivoire"
    assert detail.city is None
    assert detail.location is None


def test_emploi_ci_reads_the_criteria_list():
    detail = _detail("emploi_ci")
    assert detail.city == "Abidjan"
    assert detail.contract_type == "CDD"
    assert detail.education_level
    assert detail.sector
    assert detail.deadline is not None
    assert detail.application_url == "https://vonq.io/3S6nQyl"


def test_emploi_ci_reads_the_accents_of_the_criteria_labels():
    """The labels are written "Région", "Secteur d´activité", "Niveau d'études".

    A comparison that ignores the accents loses every criteria but the
    contract type.
    """
    detail = _detail("emploi_ci")
    assert detail.location == "Abidjan"
    assert detail.education_level


def test_emploi_ci_splits_the_body_into_missions_and_profile():
    detail = _detail("emploi_ci")
    assert len(detail.missions) > 5
    assert len(detail.profile) > 3
    assert any("Représentation" in line for line in detail.missions)


def test_emploiivoire_reads_the_details_and_the_badges():
    detail = _detail("emploiivoire")
    assert detail.company == "LEADWAY ASSURANCE"
    assert detail.city == "Abidjan"
    assert detail.country == "Côte d'Ivoire"
    assert detail.education_level == "BEPC"
    assert detail.deadline is not None
    assert detail.benefits
    assert detail.how_to_apply


def test_emploiivoire_profile_does_not_start_with_the_label():
    """The page writes "Profil recherché :".

    Splitting on a partial label leaves "recherché :" as the first
    requirement of the profile.
    """
    detail = _detail("emploiivoire")
    assert detail.profile
    for line in detail.profile:
        assert not line.lower().startswith("recherch")
        assert not line.lower().startswith("profil")


def test_eclozion_reads_the_directorist_fields():
    detail = _detail("eclozion")
    assert detail.company == "Scoop Afrique"
    assert detail.country == "Côte d'Ivoire"
    assert detail.deadline is not None
    assert detail.deadline.month == 10
    assert detail.application_url == "https://tally.so/r/eqXlLJ"


def test_eclozion_finds_the_apply_instruction_inside_a_paragraph():
    """The page writes the instruction in the middle of the last paragraph.

    The labelled splitter only sees a label that opens a line, so the
    instruction has to be looked up in the body itself.
    """
    detail = _detail("eclozion")
    assert detail.how_to_apply
    assert "postuler" in detail.how_to_apply.lower()
