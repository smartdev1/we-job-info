"""Connector for ci.eclozion-opportunities.com."""

from __future__ import annotations

import re
from html import unescape

from . import htmldom
from .base import EDITORIAL_SEARCH_TERMS, BaseHttpConnector, Offer
from .detail import (
    OfferDetail,
    apply_instructions,
    clean,
    contract_type,
    contract_type_of_text,
    country_of,
    deadline_of,
    education_of,
    experience_of,
    find_emails,
    fold_label,
    parse_date,
    split_sections,
    text_of_list,
)

# Label of the Directorist field holding the application link.
APPLY_LABEL = "lien de candidature"


class EclozionConnector(BaseHttpConnector):
    source_id = "eclozion"
    base_url = "https://ci.eclozion-opportunities.com"
    listing_path = "/all-listings/"
    # The search page ignores the page number: it returns 12 results per term.
    search_path = "/search-result/"
    search_terms = EDITORIAL_SEARCH_TERMS
    max_pages = 1
    unfiltered_pages = 1

    def parse_candidates(self, html: str) -> list[Offer]:
        offers: list[Offer] = []
        for m in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html, re.S | re.I):
            href, raw = m.group(1), m.group(2)
            if "/opportunite/" not in href:
                continue
            # Each listing is rendered as two anchors: a thumbnail whose text is
            # empty, then a plain-text anchor holding the title.
            title = " ".join(unescape(re.sub(r"<[^>]+>", " ", raw)).split())
            if len(title) < 5:
                continue
            offers.append(Offer(url=self._abs(self.base_url, href), title=title))
        return self._dedupe_by_url(offers)

    def parse_detail(self, html: str) -> OfferDetail:
        """Extract the offer fields from an eclozion detail page.

        The page is rendered by the Directorist theme: every custom field
        appears as a "directorist-single-info" block holding a label and a
        value, and the description sits in its own block of paragraphs.
        """
        detail = OfferDetail()
        root = htmldom.parse(html)

        title_node = root.find(cls="directorist-listing-details__listing-title")
        detail.title = clean(title_node.text() if title_node else None)

        for row in root.find_all(cls="directorist-single-info"):
            label_node = row.find(cls="directorist-single-info__label__text")
            value_node = row.find(cls="directorist-single-info__value")
            if label_node is None or value_node is None:
                continue
            label = fold_label(label_node.text())
            value = clean(value_node.text())
            if not value:
                continue
            if label == "localisation":
                country = country_of(value)
                if country:
                    detail.country = country
                else:
                    detail.location = value
                    detail.city = value
            elif label == "entreprise":
                detail.company = value
            elif label == "type de contrat":
                detail.contract_type = contract_type(value)
            elif label == "niveau d'etudes":
                detail.education_level = value
            elif label == "niveau d'experience":
                detail.experience = detail.experience or value
            elif label == "date limite":
                detail.deadline = parse_date(value, end_of_day=True)
            elif label == APPLY_LABEL:
                anchor = value_node.find(tag="a")
                detail.application_url = clean(anchor.href if anchor else None) or value

        body = root.find(cls="directorist-listing-details__text")
        if body is not None:
            lines = body.lines()
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
        if not detail.how_to_apply:
            detail.how_to_apply = apply_instructions(detail.description)

        if detail.education_level is None:
            detail.education_level = education_of(detail.description)
        if not detail.experience:
            detail.experience = experience_of(
                "\n".join([detail.description or "", *detail.profile])
            )
        # The "Date limite" custom field is often empty; the deadline is then
        # written inside the body ("Date limite : 25 août 2026").
        if not detail.deadline:
            detail.deadline = deadline_of(
                "\n".join([detail.description or "", *detail.profile])
            )
        # The contract type is sometimes only in the title or the body.
        if not detail.contract_type:
            detail.contract_type = contract_type_of_text(
                "\n".join([detail.title or "", detail.description or ""])
            )
        detail.contact_email = find_emails(
            detail.how_to_apply, exclude=("eclozion-opportunities.com",)
        )
        return detail
