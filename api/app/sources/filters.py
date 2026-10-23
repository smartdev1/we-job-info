"""Editorial gates applied to the offers collected from the platforms.

Two gates decide whether a collected offer belongs to the chain:

- the **theme gate** lives in :mod:`app.sources.base`: it is applied to the
  job title and keeps the web/mobile development, data/AI and cyber security
  offers;
- the **country gate** lives here: it is applied to the location the detail
  page exposes and keeps the offers published in Côte d'Ivoire.

Both gates are strict about what they exclude and lenient about what they
cannot decide. An offer whose country the page does not state is kept: the
five sources are Ivorian job boards, so a missing field is not a proof that
the job is abroad. What the page states is what counts.
"""

from __future__ import annotations

from .base import _matches
from .detail import OfferDetail, fold


# The countries the offer can be published in, in their folded form.
CI_COUNTRY_NAMES: frozenset[str] = frozenset(
    {
        "cote d'ivoire",
        "republique de cote d'ivoire",
        "ivoire",
        "ci",
        "civ",
        "ivory coast",
    }
)

# The cities of Côte d'Ivoire, written as the platforms spell them.
CI_CITY_MARKERS: tuple[str, ...] = (
    "abidjan",
    "abjan",
    "abobo",
    "adjame",
    "cocody",
    "koumassi",
    "yopougon",
    "treichville",
    "vridi",
    "blokosso",
    "port bouet",
    "deux plateaux",
    "anyama",
    "agboville",
    "grand bassam",
    "bouake",
    "gagnoa",
    "daloa",
    "segnela",
    "sinfra",
    "korhogo",
    "boundiali",
    "feresse",
    "katiola",
    "odienne",
    "bouafle",
    "san pedro",
    "soubre",
    "issia",
    "abengourou",
    "bondoukou",
    "bongouanou",
    "yamoussoukro",
    "man",
    "bueyo",
    "guiglo",
    "divo",
    "buyo",
)

# The places that prove the offer is not published in Côte d'Ivoire.
FOREIGN_MARKERS: tuple[str, ...] = (
    "france",
    "paris",
    "lyon",
    "marseille",
    "toulouse",
    "strasbourg",
    "bordeaux",
    "lille",
    "nantes",
    "grenoble",
    "nice",
    "montpellier",
    "rennes",
    "bruxelles",
    "belgique",
    "senegal",
    "dakar",
    "burkina faso",
    "ouagadougou",
    "mali",
    "bamako",
    "cameroon",
    "cameroun",
    "douala",
    "yaounde",
    "ghana",
    "accra",
    "nigeria",
    "lagos",
    "benin",
    "cotonou",
    "togo",
    "lome",
    "guinee",
    "maroc",
    "casablanca",
    "tunisie",
    "algerie",
    "allemagne",
    "berlin",
    "espagne",
    "madrid",
    "italie",
    "milan",
    "portugal",
    "royaume uni",
    "angleterre",
    "etats unis",
    "united states",
    "new york",
    "canada",
    "inde",
    "chine",
    "shanghai",
    "japon",
    "emirats arabes unis",
    "dubai",
    "afrique du sud",
)

# The three verdicts of the country gate.
CI = "cote_divoire"
FOREIGN = "etranger"
UNKNOWN = "inconnu"


def country_status(detail: OfferDetail) -> str:
    """Tell whether ``detail`` is published in Côte d'Ivoire.

    The verdict is one of:

    - ``"cote_divoire"``: the page states Côte d'Ivoire, or a city of it;
    - ``"etranger"``: the page states another country or a foreign city;
    - ``"inconnu"``: the page states no usable location.

    An unknown location is not a verdict: the sources are Ivorian job boards,
    so an offer without a location is kept and flagged for the operator.
    """
    if detail.country:
        if fold(detail.country) in CI_COUNTRY_NAMES:
            return CI
        return FOREIGN

    haystack = fold(" ".join(part for part in (detail.location, detail.city) if part))
    if not haystack.strip():
        return UNKNOWN

    for marker in CI_CITY_MARKERS:
        if _matches(haystack, marker):
            return CI
    for marker in FOREIGN_MARKERS:
        if _matches(haystack, marker):
            return FOREIGN
    return UNKNOWN


def is_cote_divoire(detail: OfferDetail) -> bool:
    """True when the offer is published in Côte d'Ivoire, or unknown.

    Only an offer that states another country is rejected.
    """
    return country_status(detail) != FOREIGN
