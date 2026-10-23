"""Connector for emploiivoire.ci."""

from __future__ import annotations

import re
from html import unescape

from . import htmldom
from .base import EDITORIAL_SEARCH_TERMS, BaseHttpConnector, Offer
from .detail import (
    OfferDetail,
    clean,
    contract_type,
    country_of,
    education_of,
    experience_of,
    find_emails,
    first_scalar,
    fold_label,
    job_posting,
    parse_date,
    split_sections,
    text_of_list,
)


class EmploiIvoireConnector(BaseHttpConnector):
    source_id = "emploiivoire"
    base_url = "https://emploiivoire.ci"
    listing_path = "/"
    # The site has its own search page; the page parameter works on it.
    search_path = "/search"
    search_terms = EDITORIAL_SEARCH_TERMS
    max_pages = 30
    unfiltered_pages = 2

    # The card wraps the whole posting: a logo, a level badge, the job title
    # in an <h3>, then the company, location, contract, deadline and the full
    # description. Only the <h3> is the title; taking the whole anchor text
    # used to produce titles like "< BEPC Agent commercial ... Description du
    # poste : ...".
    TITLE_TAG = re.compile(r"<h3[^>]*>(.*?)</h3>", re.S | re.I)
    TITLE_ALT = re.compile(r'<img[^>]+alt="([^"]+)"', re.S | re.I)

    def parse_candidates(self, html: str) -> list[Offer]:
        offers: list[Offer] = []
        for m in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html, re.S | re.I):
            href, raw = m.group(1), m.group(2)
            if "/post/" not in href:
                continue
            title_match = self.TITLE_TAG.search(raw) or self.TITLE_ALT.search(raw)
            source = title_match.group(1) if title_match else ""
            title = " ".join(unescape(re.sub(r"<[^>]+>", " ", source)).split())
            if len(title) < 5:
                continue
            offers.append(Offer(url=self._abs(self.base_url, href), title=title))
        return self._dedupe_by_url(offers)

    def parse_detail(self, html: str) -> OfferDetail:
        """Extract the offer fields from an emploiivoire detail page.

        The page opens with a schema.org JobPosting block, then states the
        company, the location, the contract type and the deadline as
        "Label : value" lines, and finally the body split in labelled
        sections.
        """
        detail = OfferDetail()
        root = htmldom.parse(html)
        posting = job_posting(html) or {}

        title_node = root.find(tag="h1")
        detail.title = clean(title_node.text() if title_node else None) or first_scalar(
            posting.get("title")
        )

        organization = posting.get("hiringOrganization") or {}
        detail.company = first_scalar(organization.get("name"))

        location = posting.get("jobLocation") or {}
        address = location.get("address") or {}
        if address.get("addressLocality"):
            locality = clean(address.get("addressLocality"))
            if country_of(locality):
                detail.country = detail.country or country_of(locality)
            else:
                detail.location = locality
                detail.city = locality
        if address.get("addressCountry"):
            detail.country = country_of(address["addressCountry"]) or clean(
                address["addressCountry"]
            )

        details = root.find(cls="job-offer-details")
        if details is not None:
            for paragraph in details.find_all(tag="p"):
                strong = paragraph.find(tag="strong")
                if strong is None:
                    continue
                label = fold_label(strong.text())
                value = clean(paragraph.text().split(":", 1)[-1] if ":" in paragraph.text() else None)
                if not value:
                    continue
                if label == "entreprise":
                    detail.company = detail.company or value
                elif label == "lieu":
                    country = country_of(value)
                    if country:
                        detail.country = detail.country or country
                    else:
                        detail.location = detail.location or value
                        if not detail.city:
                            detail.city = value
                elif label == "type de contrat":
                    detail.contract_type = detail.contract_type or contract_type(value)
                elif label == "date limite":
                    detail.deadline = detail.deadline or parse_date(
                        value, end_of_day=True
                    )

        # The badge row carries the education level and the country.
        for chip in root.find_all(cls="rounded-full"):
            text = clean(chip.text())
            if not text:
                continue
            if detail.education_level is None and education_of(text):
                detail.education_level = education_of(text)
            elif detail.country is None and country_of(text):
                detail.country = country_of(text)

        if not detail.contract_type and posting.get("employmentType"):
            detail.contract_type = contract_type(posting["employmentType"])
        if not detail.deadline and posting.get("validThrough"):
            detail.deadline = parse_date(posting["validThrough"], end_of_day=True)
        if posting.get("datePosted"):
            detail.date_posted = parse_date(posting["datePosted"])

        description_node = root.find(cls="job-description")
        if description_node is not None:
            lines = description_node.lines()
            detail.description = text_of_list(lines)
            sections = split_sections(lines)
            detail.missions = sections.get("missions", [])
            detail.profile = sections.get("profile", [])
            benefits = sections.get("benefits", [])
            if benefits:
                detail.benefits = text_of_list(benefits)
            apply_lines = sections.get("how_to_apply", [])
            if apply_lines:
                detail.how_to_apply = text_of_list(apply_lines)

        if not detail.description and posting.get("description"):
            detail.description = first_scalar(posting["description"])

        if not detail.experience:
            detail.experience = experience_of(
                "\n".join([detail.description or "", *detail.profile])
            )
        detail.contact_email = find_emails(
            detail.how_to_apply, exclude=("emploiivoire.ci",)
        )
        return detail
