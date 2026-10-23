"""Connector for jobivoire.ci."""

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
    country_of,
    education_of,
    experience_of,
    find_emails,
    first_scalar,
    fold,
    fold_label,
    job_posting,
    parse_date,
    split_sections,
    text_of_list,
)


class JobIvoireConnector(BaseHttpConnector):
    source_id = "jobivoire"
    base_url = "https://www.jobivoire.ci"
    listing_path = "/jobs"
    # The site publishes its search as a GET form on the listing page.
    search_path = "/jobs"
    search_terms = EDITORIAL_SEARCH_TERMS
    max_pages = 30
    unfiltered_pages = 2

    # Each job card exposes three anchors: a screen-reader-only link holding
    # "Voir l'offre <title>", a visible "Voir l'offire" button and an icon
    # link. Only the first one carries the title.
    CARD_LINK = re.compile(r'<a[^>]+href="([^"]*/job/[^"]+)"[^>]*>(.*?)</a>', re.S | re.I)
    SR_ONLY = re.compile(r'<span class="jb-sr-only">(.*?)</span>', re.S | re.I)
    SEE_OFFER = re.compile(r"^Voir l['’]offre\s*", re.I)

    def parse_candidates(self, html: str) -> list[Offer]:
        offers: list[Offer] = []
        for m in self.CARD_LINK.finditer(html):
            href, raw = m.group(1), m.group(2)
            sr = self.SR_ONLY.search(raw)
            if not sr:
                continue
            title = unescape(re.sub(r"<[^>]+>", " ", sr.group(1)))
            title = " ".join(self.SEE_OFFER.sub("", title).split())
            if len(title) < 5:
                continue
            offers.append(Offer(url=self._abs(self.base_url, href), title=title))
        return self._dedupe_by_url(offers)

    def parse_detail(self, html: str) -> OfferDetail:
        """Extract the offer fields from a jobivoire detail page.

        The page exposes a schema.org JobPosting block and a "quick facts"
        grid of label/value cards; the body is a prose section whose
        paragraphs open with the usual French section labels.
        """
        detail = OfferDetail()
        root = htmldom.parse(html)
        posting = job_posting(html) or {}

        title_node = root.find(cls="jb-offer-head__title")
        detail.title = clean(title_node.text() if title_node else None) or first_scalar(
            posting.get("title")
        )

        company_node = root.find(cls="jb-offer-head__company")
        organization = posting.get("hiringOrganization") or {}
        detail.company = clean(company_node.text() if company_node else None) or first_scalar(
            organization.get("name")
        )

        # Quick facts: Rémunération, Contrat, Mode de travail, Formation,
        # Domaine, Lieu de travail, Clôture.
        for card in root.find_all(cls="jb-fact-card"):
            label_node = card.find(cls="jb-fact-card__label")
            value_node = card.find(cls="jb-fact-card__value")
            if label_node is None or value_node is None:
                continue
            label = fold_label(label_node.text())
            value = clean(value_node.text())
            if not value:
                continue
            if label == "contrat":
                detail.contract_type = contract_type(value)
            elif label == "formation":
                detail.education_level = value
            elif label in ("experience", "niveau d'experience"):
                detail.experience = detail.experience or value
            elif label == "domaine":
                detail.sector = value
            elif label == "lieu de travail":
                country = country_of(value)
                if country:
                    detail.country = country
                else:
                    detail.location = value
                    detail.city = value
            elif label == "cloture":
                detail.deadline = parse_date(value, end_of_day=True)
            elif label == "remuneration":
                if "non communiquee" not in fold(value):
                    detail.salary = value

        location = posting.get("jobLocation") or {}
        address = location.get("address") or {}
        if not detail.country and address.get("addressCountry"):
            detail.country = country_of(address["addressCountry"]) or clean(
                address["addressCountry"]
            )
        if not detail.location and address.get("addressLocality"):
            locality = clean(address.get("addressLocality"))
            if country_of(locality):
                detail.country = detail.country or country_of(locality)
            else:
                detail.location = locality
                detail.city = locality

        if not detail.contract_type and posting.get("employmentType"):
            detail.contract_type = contract_type(posting["employmentType"])
        if not detail.deadline and posting.get("validThrough"):
            detail.deadline = parse_date(posting["validThrough"], end_of_day=True)
        if posting.get("datePosted"):
            detail.date_posted = parse_date(posting["datePosted"])

        prose = root.find(cls="jb-prose")
        if prose is not None:
            lines = prose.lines()
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

        # The body closes with a "Pour postuler, ou" line that points to the
        # notice of the site: the notice holds the real instruction.
        notice = root.find(cls="jb-notice")
        if notice is not None:
            detail.how_to_apply = clean(notice.text()) or detail.how_to_apply
        if not detail.how_to_apply:
            detail.how_to_apply = apply_instructions(detail.description)

        if not detail.application_url:
            apply_link = root.find(cls="jb-apply__actions")
            if apply_link is not None:
                for anchor in apply_link.find_all(tag="a"):
                    href = anchor.href
                    if href and href.startswith("http"):
                        detail.application_url = href
                        break

        if not detail.experience:
            detail.experience = experience_of(
                "\n".join([detail.description or "", *detail.profile])
            )
        detail.contact_email = find_emails(
            detail.how_to_apply, exclude=("jobivoire.ci",)
        )
        return detail
