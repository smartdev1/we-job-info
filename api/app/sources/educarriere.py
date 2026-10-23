"""Connector for educarriere.ci."""

from __future__ import annotations

import re
from html import unescape
from urllib.parse import urlparse

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
    job_posting,
    parse_date,
    split_sections,
    text_of_list,
)


class EducarriereConnector(BaseHttpConnector):
    source_id = "educarriere"
    base_url = "https://emploi.educarriere.ci"
    listing_path = "/page/all"
    # The site exposes no job search and no page parameter: "/page/all"
    # returns the same 41 offers whatever the query string is.
    max_pages = 1

    # Job links look like /offre-<id>-<slug>.html.
    JOB_LINK = re.compile(r'/offre-\d+[^"\'<>]*\.html', re.I)
    # Each card is an anchor holding: a logo, the job title in a bold div, the
    # company name, the deadline and a category badge. Only the bold div is
    # the title. The category badge is a <span> that also declares
    # font-weight:700, so the element name has to be part of the pattern.
    TITLE_DIV = re.compile(r"<div[^>]*font-weight:\s*700[^>]*>(.*?)</div>", re.S | re.I)

    def parse_candidates(self, html: str) -> list[Offer]:
        offers: list[Offer] = []
        for m in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html, re.S | re.I):
            href, raw = m.group(1), m.group(2)
            if not self.JOB_LINK.search(href):
                continue
            title_match = self.TITLE_DIV.search(raw)
            source = title_match.group(1) if title_match else raw
            title = " ".join(unescape(re.sub(r"<[^>]+>", " ", source)).split())
            if len(title) < 5:
                continue
            offers.append(Offer(url=self._abs(self.base_url, href), title=title))
        return self._dedupe_by_url(offers)

    def parse_detail(self, html: str) -> OfferDetail:
        """Extract the offer fields from an educarriere detail page.

        The page states the sector, the location, the level and the deadline
        as "joh-stat" label/value pairs, and publishes a schema.org
        JobPosting block.
        """
        detail = OfferDetail()
        root = htmldom.parse(html)
        posting = job_posting(html) or {}

        title_node = root.find(cls="joh-title")
        detail.title = clean(title_node.text() if title_node else None) or first_scalar(
            posting.get("title")
        )

        company_node = root.find(cls="joh-company-name")
        organization = posting.get("hiringOrganization") or {}
        detail.company = clean(company_node.text() if company_node else None) or first_scalar(
            organization.get("name")
        )

        for stat in root.find_all(cls="joh-stat"):
            label_node = stat.find(cls="joh-stat__label")
            value_node = stat.find(cls="joh-stat__val")
            if label_node is None or value_node is None:
                continue
            label = fold_label(label_node.text())
            value = clean(value_node.text())
            if not value:
                continue
            if label == "secteur":
                detail.sector = value
            elif label == "lieu":
                country = country_of(value)
                if country:
                    detail.country = country
                else:
                    detail.location = value
                    detail.city = value
            elif label == "niveau":
                detail.education_level = value
            elif label == "niveau d'experience":
                detail.experience = detail.experience or value
            elif label == "date limite":
                detail.deadline = parse_date(value, end_of_day=True)

        location = posting.get("jobLocation") or {}
        address = location.get("address") or {}
        if not detail.country and address.get("addressCountry"):
            detail.country = country_of(address["addressCountry"]) or clean(
                address["addressCountry"]
            )
        if not detail.location and address.get("addressLocality"):
            locality = clean(address["addressLocality"])
            if country_of(locality):
                detail.country = detail.country or country_of(locality)
            else:
                detail.location = locality
                detail.city = locality
        if not detail.sector and posting.get("industry"):
            detail.sector = first_scalar(posting["industry"])
        if not detail.contract_type and posting.get("employmentType"):
            detail.contract_type = contract_type(posting["employmentType"])
        if not detail.deadline and posting.get("validThrough"):
            detail.deadline = parse_date(posting["validThrough"], end_of_day=True)
        if posting.get("datePosted"):
            detail.date_posted = parse_date(posting["datePosted"])

        date_node = root.find(cls="joh-date")
        if date_node is not None and detail.date_posted is None:
            match = re.search(r"(\d{1,2}[/.]\d{1,2}[/.]\d{4})", date_node.text())
            if match:
                detail.date_posted = parse_date(match.group(1))

        body = root.find(cls="offer-description-wrap")
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
            detail.application_url = self._external_link(body)
            detail.contact_email = find_emails(
                detail.how_to_apply, exclude=("educarriere.net", "educarriere.ci")
            )
        if not detail.experience:
            detail.experience = experience_of(
                "\n".join([detail.description or "", *detail.profile])
            )
        return detail

    def _external_link(self, node) -> str | None:
        """Return the first link of the body that leaves the platform.

        The apply button of the site is an anchor to a section of the same
        page; the real application link is the one the recruiter put in the
        body of the offer.
        """
        host = urlparse(self.base_url).netloc
        for anchor in node.find_all(tag="a"):
            href = anchor.href
            if not href or not href.startswith("http"):
                continue
            if urlparse(href).netloc == host:
                continue
            if "facebook.com" in href or "wa.me" in href or "linkedin.com" in href:
                continue
            return href
        return None
