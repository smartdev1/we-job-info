"""Shared vocabulary for turning a job detail page into structured fields.

The connectors parse the markup of their own site and return an
:class:`OfferDetail`. Everything that is not site-specific lives here:
the JSON-LD ``JobPosting`` reader, the date and contract-type normalisers,
and the section splitter that turns a free-form body into missions /
profile / benefits.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")

_MONTHS_FR = {
    "janvier": 1, "janv": 1, "fevrier": 2, "fevr": 2, "mars": 3, "avril": 4,
    "avr": 4, "mai": 5, "juin": 6, "juillet": 7, "juil": 7, "aout": 8,
    "septembre": 9, "sept": 9, "octobre": 10, "oct": 10, "novembre": 11,
    "nov": 11, "decembre": 12, "dec": 12,
}
_MONTHS_EN = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11,
    "december": 12,
}

# schema.org employmentType -> the wording the channel uses.
CONTRACT_TYPES = {
    "FULL_TIME": "CDI",
    "PART_TIME": "Temps partiel",
    "CONTRACTOR": "Freelance",
    "TEMPORARY": "CDD",
    "INTERN": "Stage",
    "VOLUNTEER": "Bénévolat",
    "PER_DIEM": "Journalier",
    "OTHER": None,
}

# Section labels recognised in a job body, mapped to the target field.
# The aliases are folded (lower case, no accents, straight quotes) because
# the sites write the same label in as many ways: "Profil recherché",
# "Profil recherche", "Profil Requise".
# The aliases are ordered from the most specific to the most generic: the
# first one that opens a line wins, so "missions de l'emploi" has to come
# before "missions".
SECTION_LABELS: dict[str, tuple[str, ...]] = {
    "missions": (
        "missions de l'emploi", "missions principales", "responsabilites et taches",
        "responsabilites", "mission principale", "missions", "taches",
    ),
    "profile": (
        "profil recherche pour le poste", "profil recherche", "profil requis",
        "competences requises", "qualifications", "exigences", "profil",
        "competences",
    ),
    "benefits": (
        "ce que nous offrons", "ce que nous proposons", "avantages",
        "conditions remuneration",
    ),
    "how_to_apply": (
        "pour postuler", "comment postuler", "processus de candidature",
        "candidature", "postuler",
    ),
}

# Countries the five sites advertise, so a "Lieu" that is really a country
# does not end up in the city column.
COUNTRY_ALIASES = {
    "cote d'ivoire": "Côte d'Ivoire",
    "cote d’ivoire": "Côte d'Ivoire",
    "côte d'ivoire": "Côte d'Ivoire",
    "côte d’ivoire": "Côte d'Ivoire",
    "ivoire": "Côte d'Ivoire",
    "ci": "Côte d'Ivoire",
    "senegal": "Sénégal",
    "burkina faso": "Burkina Faso",
    "mali": "Mali",
    "cameroon": "Cameroun",
    "cameroun": "Cameroun",
    "ghana": "Ghana",
    "nigeria": "Nigeria",
    "benin": "Bénin",
    "togo": "Togo",
    "guinea": "Guinée",
    "guinee": "Guinée",
    "afrique du sud": "Afrique du Sud",
}

# Education levels as the sites spell them.
EDUCATION_RE = re.compile(
    r"\b(BEPC|BAC\s*\+?\s*\d*|BTS|DUT|LICENCE|MASTER|DOCTORAT|ENGINEER|INGENIEUR)\b",
    re.I,
)

_BULLET = re.compile(r"^[-•●▪*\s]+")
_ISO_DATE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}:\d{2}(?::\d{2})?))?")
_NUMERIC_DATE = re.compile(r"^(\d{1,2})[/.](\d{1,2})[/.](\d{4})")
_TEXTUAL_DATE = re.compile(r"^(\d{1,2})\s+([A-Za-zÀ-ÿ]{3,12})\.?,?\s+(\d{4})")
_MONTH_FIRST_DATE = re.compile(r"^([A-Za-zÀ-ÿ]{3,12})\.?\s+(\d{1,2}),?\s+(\d{4})")

# Characters that separate a label from its value.
_SEPARATORS = " :–—-».,"

# Quotes and accents used inconsistently by the sites.
_QUOTES = {"’": "'", "‘": "'", "´": "'", "`": "'", "“": '"', "”": '"'}


def fold(text: str) -> str:
    """Lower-case a text, drop its accents and straighten its quotes.

    The result keeps the length of the input, so a match found in the
    folded text can be used to slice the original one.
    """
    out: list[str] = []
    for char in text:
        if char in _QUOTES:
            out.append(_QUOTES[char])
            continue
        decomposed = unicodedata.normalize("NFKD", char)
        base = "".join(c for c in decomposed if not unicodedata.combining(c))
        # Some characters decompose into several (ligatures): keeping the
        # original one is the only way to preserve the length of the text.
        out.append(base.lower() if len(base) == 1 else char)
    return "".join(out)


@dataclass
class OfferDetail:
    """A job offer extracted from a detail page.

    Every field is optional: a page that does not expose a value leaves it
    unset rather than filling it with a guess.
    """

    title: str | None = None
    company: str | None = None
    location: str | None = None
    city: str | None = None
    country: str | None = None
    contract_type: str | None = None
    education_level: str | None = None
    experience: str | None = None
    sector: str | None = None
    description: str | None = None
    missions: list[str] = field(default_factory=list)
    profile: list[str] = field(default_factory=list)
    benefits: str | None = None
    how_to_apply: str | None = None
    contact_email: str | None = None
    application_url: str | None = None
    deadline: datetime | None = None
    date_posted: datetime | None = None
    salary: str | None = None

    def as_columns(self) -> dict[str, Any]:
        """Return the fields as the ``offers`` table columns."""
        return {
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "city": self.city,
            "country": self.country,
            "contract_type": self.contract_type,
            "education_level": self.education_level,
            "experience": self.experience,
            "sector": self.sector,
            "description": self.description,
            "missions": self.missions or None,
            "profile": self.profile or None,
            "benefits": self.benefits,
            "how_to_apply": self.how_to_apply,
            "contact_email": self.contact_email,
            "application_url": self.application_url,
            "deadline": self.deadline,
        }


# --------------------------------------------------------------------------
# JSON-LD
# --------------------------------------------------------------------------
_LD_BLOCK = re.compile(
    r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.S | re.I,
)


def json_ld_blocks(html: str) -> list[Any]:
    """Return every parsable JSON-LD block of a page."""
    out: list[Any] = []
    for raw in _LD_BLOCK.findall(html):
        candidate = raw.strip()
        if not candidate:
            continue
        try:
            out.append(json.loads(candidate))
        except ValueError:
            # Some sites emit a JSON-LD block with unescaped newlines inside a
            # string. The block is then unusable as JSON; the caller falls
            # back to the markup.
            continue
    return out


def job_posting(html: str) -> dict[str, Any] | None:
    """Return the schema.org ``JobPosting`` object of a page, if any."""
    for block in json_ld_blocks(html):
        items = block if isinstance(block, list) else [block]
        for item in items:
            if isinstance(item, dict) and item.get("@type") == "JobPosting":
                return _flatten_posting(item)
    return None


def _flatten_posting(posting: dict[str, Any]) -> dict[str, Any]:
    """Reduce the lists of a JobPosting to their first element.

    schema.org allows a list for several fields: ``employmentType`` is
    ``["FULL_TIME"]`` on some sites and ``"FULL_TIME"`` on others,
    ``jobLocation`` holds a list of places, ``hiringOrganization`` a list of
    organisations. The extraction wants one value, so the list is reduced
    here rather than at every call site.
    """
    out: dict[str, Any] = {}
    for key, value in posting.items():
        if isinstance(value, list):
            out[key] = value[0] if value else None
        else:
            out[key] = value
    return out


# Scalar fields read from a JobPosting block, in the order they are looked up.
_SCALARS = ("title", "datePosted", "validThrough", "employmentType", "industry")

_SCALAR_RE = {
    name: re.compile(r'"%s"\s*:\s*"((?:[^"\\]|\\.)*)"' % name)
    for name in _SCALARS
}
_ORG_NAME_RE = re.compile(
    r'"hiringOrganization"\s*:\s*\{[^{}]*?"name"\s*:\s*"((?:[^"\\]|\\.)*)"', re.S
)
_ADDRESS_RE = {
    name: re.compile(r'"%s"\s*:\s*"((?:[^"\\]|\\.)*)"' % name)
    for name in ("addressLocality", "addressRegion", "addressCountry")
}


def _unescape_json_string(value: str) -> str:
    try:
        return json.loads(f'"{value}"')
    except ValueError:
        return value


def job_posting_scalars(html: str) -> dict[str, Any]:
    """Read the flat fields of a ``JobPosting`` block, tolerating broken JSON.

    One of the sites publishes a JSON-LD block whose description contains
    unescaped newlines, which makes the whole block unparsable. The scalar
    fields around it are still perfectly readable in the raw text, so they
    are recovered from there instead of being lost.
    """
    parsed = job_posting(html)
    if parsed is not None:
        out: dict[str, Any] = {name: parsed.get(name) for name in _SCALARS}
        organization = parsed.get("hiringOrganization") or {}
        if isinstance(organization, dict):
            out["company"] = organization.get("name")
        address = ((parsed.get("jobLocation") or {}).get("address")) or {}
        if isinstance(address, dict):
            out["city"] = address.get("addressLocality")
            out["region"] = address.get("addressRegion")
            out["country"] = address.get("addressCountry")
        return out

    for raw in _LD_BLOCK.findall(html):
        if '"JobPosting"' not in raw:
            continue
        out = {}
        for name, pattern in _SCALAR_RE.items():
            match = pattern.search(raw)
            if match:
                out[name] = _unescape_json_string(match.group(1))
        match = _ORG_NAME_RE.search(raw)
        if match:
            out["company"] = _unescape_json_string(match.group(1))
        for name, pattern in _ADDRESS_RE.items():
            match = pattern.search(raw)
            if match:
                out[name] = _unescape_json_string(match.group(1))
        return out
    return {}


# --------------------------------------------------------------------------
# Normalisers
# --------------------------------------------------------------------------
def clean(value: str | None) -> str | None:
    """Collapse whitespace; empty strings become ``None``."""
    if value is None:
        return None
    cleaned = " ".join(value.split())
    return cleaned or None


def parse_date(value: str | None, *, end_of_day: bool = False) -> datetime | None:
    """Parse a date written in one of the formats the five sites use.

    Handles ISO timestamps, ``26/10/2026``, ``26 octobre 2026``, ``31 déc. 2027``
    and ``October 1, 2026``. A date without a time is anchored at midnight UTC,
    or at the end of the day when ``end_of_day`` is set (deadlines).
    """
    if not value:
        return None
    text = value.strip()

    iso = _ISO_DATE.match(text)
    if iso:
        day = datetime(
            int(iso.group(1)), int(iso.group(2)), int(iso.group(3)),
            tzinfo=timezone.utc,
        )
        if iso.group(4):
            time_parts = [int(p) for p in iso.group(4).split(":")]
            day = day.replace(hour=time_parts[0], minute=time_parts[1],
                              second=time_parts[2] if len(time_parts) > 2 else 0)
        return day

    numeric = _NUMERIC_DATE.match(text)
    if numeric:
        day, month, year = (int(g) for g in numeric.groups())
        try:
            return datetime(year, month, day, tzinfo=timezone.utc)
        except ValueError:
            return None

    textual = _TEXTUAL_DATE.match(text)
    if textual:
        day, month_name, year = textual.groups()
        month = _month_number(month_name)
        if month:
            try:
                return datetime(int(year), month, int(day), tzinfo=timezone.utc)
            except ValueError:
                return None

    month_first = _MONTH_FIRST_DATE.match(text)
    if month_first:
        month_name, day, year = month_first.groups()
        month = _month_number(month_name)
        if month:
            try:
                return datetime(int(year), month, int(day), tzinfo=timezone.utc)
            except ValueError:
                return None
    return None


def _month_number(name: str) -> int | None:
    """Return the month number of a French or English month name."""
    key = fold(name).rstrip(".")
    return _MONTHS_FR.get(key) or _MONTHS_EN.get(key)


def first_scalar(value: Any) -> str | None:
    """Return the first usable string of a JSON-LD value.

    schema.org allows a list for several fields: ``employmentType`` is
    ``["FULL_TIME"]`` on some sites and ``"FULL_TIME"`` on others. A list is
    therefore read as its first element.
    """
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        for item in value:
            scalar = first_scalar(item)
            if scalar:
                return scalar
        return None
    if isinstance(value, str):
        return clean(value)
    if isinstance(value, (int, float)):
        return str(value)
    return None


CONTRACT_SEPARATOR = re.compile(r"\s*[-–—/,|]\s*")


def contract_type(value: str | list | None) -> str | None:
    """Normalise a contract type to the wording used by the channel.

    Some platforms publish a multi-select list as a single string ("CDI - CDD -
    Stage"). Only the first contract is kept: the channel announces one
    contract per offer.
    """
    text = first_scalar(value)
    if not text:
        return None
    parts = [part for part in CONTRACT_SEPARATOR.split(text) if part]
    for part in parts:
        mapped = CONTRACT_TYPES.get(part.upper())
        if mapped:
            return mapped
    return clean(parts[0]) if parts else clean(text)


def strip_bullet(text: str) -> str:
    """Remove a leading list marker from a line."""
    return _BULLET.sub("", text).strip()


def _starts_with_label(line: str, alias: str) -> bool:
    """Tell whether a line opens with a section label.

    The comparison ignores case, accents and the quote style of the sites,
    and only accepts a label that is followed by a separator or by nothing.
    """
    folded = fold(line)
    alias = fold(alias)
    if not folded.startswith(alias):
        return False
    rest = folded[len(alias):]
    return rest == "" or rest[0] in _SEPARATORS


def split_sections(
    lines: list[str], labels: dict[str, tuple[str, ...]] | None = None
) -> dict[str, list[str]]:
    """Split a job body into labelled sections.

    A line that opens with a known label starts a new section; the rest of
    that line, if any, is the first entry of the section. Lines that follow
    are appended until the next label.
    """
    labels = labels or SECTION_LABELS
    sections: dict[str, list[str]] = {key: [] for key in labels}
    current: str | None = None

    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        folded = fold(line)
        matched: tuple[str, int] | None = None
        for key, aliases in labels.items():
            for alias in aliases:
                alias_folded = fold(alias)
                if not folded.startswith(alias_folded):
                    continue
                rest = folded[len(alias_folded):]
                if rest and rest[0] not in _SEPARATORS:
                    continue
                matched = (key, len(alias_folded))
                break
            if matched:
                break
        if matched:
            key, length = matched
            rest = line[length:].lstrip(_SEPARATORS)
            current = key
            if rest:
                sections[key].append(strip_bullet(rest))
            continue
        if current is not None:
            sections[current].append(strip_bullet(line))
    return sections


def find_emails(text: str | None, *, exclude: tuple[str, ...] = ()) -> str | None:
    """Return the first e-mail address of a text, ignoring excluded domains."""
    if not text:
        return None
    for match in EMAIL_RE.findall(text):
        lowered = match.lower()
        if any(bad in lowered for bad in exclude):
            continue
        return match
    return None


def fold_label(value: str | None) -> str:
    """Return the comparable form of a field label.

    The sites write the same label with a different case, with accents, with
    a straight or a curly apostrophe, and sometimes with a trailing colon.
    The result is meant to be compared with the keys of a label mapping.
    """
    if not value:
        return ""
    return fold(value).strip().strip(_SEPARATORS).strip()


def country_of(value: str | None) -> str | None:
    """Return the country a location refers to, or ``None``."""
    if not value:
        return None
    return COUNTRY_ALIASES.get(value.strip().lower())


def education_of(value: str | None) -> str | None:
    """Return the education level mentioned by a text, or ``None``."""
    if not value:
        return None
    match = EDUCATION_RE.search(value)
    if not match:
        return None
    return " ".join(match.group(1).upper().split())


_CONTRACT_WORD_RE = re.compile(
    r"\b(CDI|CDD|Stage|Stagiaire|int[ée]rim|Freelance|Prestation|Contrat\s+de\s+prestation)\b",
    re.I,
)


def contract_type_of_text(value: str | None) -> str | None:
    """Return the contract type mentioned by a text, or ``None``.

    The labelled field is empty on some offers and the contract type is only
    written in the title or the body ("Stage", "CDD", "CDI"), so the text is
    scanned as a fallback.
    """
    if not value:
        return None
    for match in _CONTRACT_WORD_RE.finditer(value):
        word = match.group(1).strip()
        mapped = CONTRACT_TYPES.get(word.upper())
        if mapped:
            return mapped
        folded = fold(word)
        if "stagiaire" in folded or folded == "stage":
            return "Stage"
        if folded == "cdi":
            return "CDI"
        if folded == "cdd":
            return "CDD"
        if "interim" in folded or "int[ée]rim" in folded:
            return "Intérim"
        if "freelance" in folded:
            return "Freelance"
    return None


_DEADLINE_RE = re.compile(
    r"(?:date\s+limite|date\s+limit|deadline|expiration)\s*[:\-]?\s*([^\n.;]{3,60})",
    re.I,
)


def deadline_of(value: str | None) -> datetime | None:
    """Return the deadline mentioned by a text, or ``None``.

    The "Date limite : 25 août 2026" wording is written inside the body of
    some offers instead of in a labelled field, so the deadline is recovered
    from the free text when the labelled field is empty.
    """
    if not value:
        return None
    for raw in value.splitlines():
        line = raw.strip()
        if not line:
            continue
        match = _DEADLINE_RE.search(line)
        if not match:
            continue
        parsed = parse_date(match.group(1).strip(), end_of_day=True)
        if parsed is not None:
            return parsed
    return None


_EXPERIENCE_RE = re.compile(
    r"(\d{1,2})\s*(?:à|-|et)?\s*\d{0,2}\s*ans?\s+d['’]?exp[ée]rience", re.I
)


def experience_of(value: str | None) -> str | None:
    """Return the experience asked for by a text, or ``None``.

    Only the explicit "N ans d'expérience" wording is recognised: a number
    of years mentioned in passing is not an experience requirement.
    """
    if not value:
        return None
    match = _EXPERIENCE_RE.search(value)
    if not match:
        return None
    years = int(match.group(1))
    return f"{years} ans d'expérience" if years > 1 else "1 an d'expérience"


def text_of_list(items: list[str]) -> str | None:
    """Join a list of lines into a single readable block."""
    cleaned = [strip_bullet(item) for item in items if strip_bullet(item)]
    if not cleaned:
        return None
    return "\n".join(cleaned)


_APPLY_MARKERS = ("pour postuler", "postuler", "candidater")


def apply_instructions(text: str | None) -> str | None:
    """Return the sentence of a body that tells how to apply.

    Some sites write the instruction in the middle of a paragraph instead
    of opening a labelled section, so the labelled splitter never sees it.
    """
    if not text:
        return None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        folded = fold(line)
        for marker in _APPLY_MARKERS:
            index = folded.find(marker)
            if index == -1:
                continue
            sentence = line[index:].strip()
            # Keep the sentence, not the rest of the paragraph.
            for stop in (". ", "! ", "? "):
                cut = sentence.find(stop)
                if cut != -1:
                    sentence = sentence[: cut + 1]
                    break
            return clean(sentence)
    return None
