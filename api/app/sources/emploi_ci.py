"""Connector for emploi.ci."""

from __future__ import annotations

import re
from html import unescape

from . import htmldom
from .base import BaseHttpConnector, Offer
from .detail import (
    OfferDetail,
    clean,
    contract_type,
    country_of,
    experience_of,
    find_emails,
    first_scalar,
    fold_label,
    job_posting_scalars,
    parse_date,
    split_sections,
    text_of_list,
)

# How the "Critères de l'annonce" list names its fields.
CRITERIA_LABELS = {
    "metier": "sector",
    "secteur d'activite": "sector",
    "type de contrat": "contract_type",
    "region": "location",
    "ville": "city",
    "niveau d'experience": "experience",
    "niveau d'etudes": "education_level",
}


class EmploiCiConnector(BaseHttpConnector):
    source_id = "emploi_ci"
    base_url = "https://www.emploi.ci"
    listing_path = "/recherche-jobs-cote-ivoire"
    # The site is a Drupal application whose search is a POST form: a GET on
    # the query string does not filter the results. The pagination is the
    # only lever, and it exposes 24 offers per page.
    max_pages = 25

    JOB_LINK = re.compile(r"/offre-emploi[^/]*/[^/?#]*-\d+(?:[/?#]|$)", re.I)

    def parse_candidates(self, html: str) -> list[Offer]:
        offers: list[Offer] = []
        for m in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html, re.S | re.I):
            href, raw = m.group(1), m.group(2)
            if not self.JOB_LINK.search(href):
                continue
            title = " ".join(unescape(re.sub(r"<[^>]+>", " ", raw)).split())
            if len(title) < 5:
                continue
            offers.append(Offer(url=self._abs(self.base_url, href), title=title))
        return self._dedupe_by_url(offers)

    def parse_detail(self, html: str) -> OfferDetail:
        """Extract the offer fields from an emploi.ci detail page.

        The page states the criteria of the offer as a "Label : value" list
        and splits the body into a description, a set of qualifications and
        the criteria. Its JSON-LD block is published with unescaped newlines
        and cannot be parsed as JSON, so the scalar fields are recovered
        from the raw block instead.
        """
        detail = OfferDetail()
        root = htmldom.parse(html)
        scalars = job_posting_scalars(html)

        title_node = root.find(tag="h1")
        detail.title = clean(title_node.text() if title_node else None) or first_scalar(
            scalars.get("title")
        )

        company_block = root.find(cls="card-block-company")
        if company_block is not None:
            first_item = company_block.find(tag="li")
            if first_item is not None:
                detail.company = clean(first_item.text())
        if not detail.company:
            detail.company = first_scalar(scalars.get("company"))

        for item in root.find_all(cls="arrow-list"):
            for entry in item.find_all(tag="li"):
                label_node = entry.find(tag="strong")
                if label_node is None:
                    continue
                label = fold_label(label_node.text())
                value = clean(entry.text()[len(label_node.text()):].lstrip(" :"))
                if not value:
                    continue
                field = CRITERIA_LABELS.get(label)
                if field == "sector":
                    detail.sector = detail.sector or value
                elif field == "contract_type":
                    detail.contract_type = detail.contract_type or contract_type(value)
                elif field == "location":
                    country = country_of(value)
                    if country:
                        detail.country = detail.country or country
                    else:
                        detail.location = detail.location or value
                elif field == "city":
                    detail.city = detail.city or value
                elif field == "experience":
                    detail.experience = detail.experience or value
                elif field == "education_level":
                    detail.education_level = detail.education_level or value

        if scalars.get("city") and not detail.city:
            detail.city = clean(scalars.get("city"))
        if scalars.get("country"):
            detail.country = country_of(scalars.get("country")) or clean(
                scalars.get("country")
            )
        if not detail.contract_type and scalars.get("employmentType"):
            detail.contract_type = contract_type(scalars["employmentType"])
        if not detail.deadline and scalars.get("validThrough"):
            detail.deadline = parse_date(scalars["validThrough"], end_of_day=True)
        if scalars.get("datePosted"):
            detail.date_posted = parse_date(scalars["datePosted"])

        details = root.find(cls="page-application-details")
        if details is not None:
            published = re.search(r"(\d{1,2}[/.]\d{1,2}[/.]\d{4})", details.text())
            if published and detail.date_posted is None:
                detail.date_posted = parse_date(published.group(1))

        description_node = root.find(cls="job-description")
        if description_node is not None:
            lines = description_node.lines()
            detail.description = text_of_list(lines)
            sections = split_sections(lines)
            detail.missions = sections.get("missions", [])
            detail.profile = sections.get("profile", [])

        qualifications = root.find(cls="job-qualifications")
        if qualifications is not None:
            lines = qualifications.lines()
            profile_lines = split_sections(lines).get("profile", [])
            detail.profile = detail.profile or profile_lines
            if not detail.profile:
                detail.profile = [line for line in lines if line]

        for anchor in root.find_all(tag="a"):
            if "postuler" in anchor.text().lower() and anchor.href:
                if anchor.href.startswith("http"):
                    detail.application_url = anchor.href
                    break

        detail.contact_email = find_emails(
            detail.how_to_apply or detail.description, exclude=("emploi.ci",)
        )
        return detail
