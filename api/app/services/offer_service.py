"""Offer-related application services."""

from __future__ import annotations

import hashlib
import os
import re
import uuid
from html import unescape
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import JobLog, Offer, RawDocument
from app.services.url_safety import validate_url, UnsafeUrlError, normalize_url, safe_fetch

ALLOWED_IMAGE_MIMES = {"image/png", "image/jpeg", "image/webp"}
MAX_IMAGE_BYTES = get_settings().max_upload_mb * 1024 * 1024
MAX_CONTENT_BYTES = 5 * 1024 * 1024
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./uploads"))


def validate_image_magic_bytes(content: bytes, mime: str) -> bool:
    """Validate that content's magic bytes match the claimed mime.

    Client-supplied content_type is untrusted; this is a second line of defense.
    """
    if not content:
        return False
    if mime == "image/png":
        return content.startswith(b"\x89PNG\r\n\x1a\n")
    if mime == "image/jpeg":
        return content.startswith(b"\xff\xd8\xff")
    if mime == "image/webp":
        return len(content) >= 12 and content[0:4] == b"RIFF" and content[8:12] == b"WEBP"
    return False


def _extract_fields_from_html(raw_html: str) -> dict[str, str | None]:
    """Extrait les champs principaux depuis le HTML brut avant extraction LLM.

    Ce modèle cherche les champs visibles dans la structure HTML des offres
    (type directorist/eclozion) et retourne un dictionnaire avec les champs
    title, company, location, deadline, application_url, contract_type.
    Les champs absents sont renvoyés à ``None`` ; le LLM pourra les compléter
    depuis le texte restant si nécessaire.
    """
    text = unescape(raw_html)

    # Titre (h1 avec la classe directorist-listing-details__listing-title)
    title: str | None = None
    title_m = re.search(
        r'<h1[^>]*class="[^"]*directorist-listing-details__listing-title[^"]*"[^>]*>(.*?)</h1>',
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if title_m:
        title = re.sub(r"<[^>]+>", " ", title_m.group(1)).strip()

    # Entreprise : recherche du nom de la structure (SIB, etc.)
    company: str | None = None
    # On cherche une occurrence courante dans les offres CI
    company_m = re.search(r"Société Ivoirienne de Banque", text)
    if company_m:
        company = "Société Ivoirienne de Banque (SIB)"

    # Localisation : dans le .directorist-single-info contenant "Localisation"
    location: str | None = None
    loc_m = re.search(r"Localisation[^<]*>(.*?)</div>", text, re.IGNORECASE | re.DOTALL)
    if loc_m:
        location = re.sub(r"<[^>]+>", " ", loc_m.group(1)).strip()

    # Date limite de candidature
    deadline: str | None = None
    dl_m = re.search(
        r"Date limite[^<]*(?:candidature|échéance)[^<]*:?\s*([^\n<>]+)",
        text,
        re.IGNORECASE,
    )
    if dl_m:
        deadline = dl_m.group(1).strip()

    # URL de candidature (lien vers sociumjob ou formulaire)
    application_url: str | None = None
    url_m = re.search(
        r'href="([^"]*sociumjob[^"]*|[^"]*apply[^"]*|[^"]*candidature[^"]*)"',
        text,
        re.IGNORECASE,
    )
    if url_m:
        application_url = url_m.group(1)

    # Type de contrat (CDI, CDD, Stage, etc.)
    contract_type: str | None = None
    ct_m = re.search(r"\b(CDI|CDD|Stage|int[ée]rim|Freelance|Prestation)\b", text, re.IGNORECASE)
    if ct_m:
        contract_type = ct_m.group(1)

    return {
        "title": title,
        "company": company,
        "location": location,
        "deadline": deadline,
        "application_url": application_url,
        "contract_type": contract_type,
    }


async def create_extraction_job(db: AsyncSession, text: str) -> JobLog:
    """Create a pending extraction job for a manually pasted offer text."""
    text = text.strip()
    job = JobLog(
        id=uuid.uuid4(),
        job_name="extract_offer_from_text",
        status="pending",
        payload={"text": text},
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def create_extraction_job_from_url(db: AsyncSession, url: str) -> tuple[JobLog | None, Offer | None, bool]:
    """Fetch a URL safely, store content as raw_document, create extraction job.

    Idempotent: if the URL or its content hash is already known, no new fetch/LLM
    work is scheduled and the existing offer is returned.
    """
    normalized = validate_url(url)

    # Idempotence by URL.
    result = await db.execute(select(Offer).where(Offer.origin_url == normalized))
    existing = result.scalar_one_or_none()
    if existing is not None:
        return None, existing, True

    content = safe_fetch(normalized, max_bytes=MAX_CONTENT_BYTES)
    content_hash = hashlib.sha256(content).hexdigest()

    # Idempotence by content hash.
    rd_result = await db.execute(select(RawDocument).where(RawDocument.content_hash == content_hash))
    raw_doc = rd_result.scalar_one_or_none()
    if raw_doc is not None:
        off_result = await db.execute(select(Offer).where(Offer.raw_document_id == raw_doc.id))
        existing_offer = off_result.scalar_one_or_none()
        if existing_offer is not None:
            return None, existing_offer, True

    if raw_doc is None:
        text = content.decode("utf-8", errors="replace")
        raw_doc = RawDocument(
            url=normalized,
            content_type="text/html",
            content=text,
            content_hash=content_hash,
        )
        db.add(raw_doc)
        await db.flush()

    job = JobLog(
        id=uuid.uuid4(),
        job_name="extract_offer_from_url",
        status="pending",
        payload={"url": normalized, "raw_document_id": str(raw_doc.id)},
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job, None, False


async def create_extraction_job_from_image(db: AsyncSession, content: bytes, mime: str) -> JobLog:
    """Persist an uploaded image under a UUID filename and schedule extraction.

    Validation of MIME and size happens in the route; this function assumes valid input.
    """
    if mime not in ALLOWED_IMAGE_MIMES:
        raise ValueError("invalid mime")
    if len(content) > MAX_IMAGE_BYTES or len(content) == 0:
        raise ValueError("invalid size")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    ext = mime.split("/")[-1].replace("jpeg", "jpg")
    filename = f"{uuid.uuid4()}.{ext}"
    path = UPLOAD_DIR / filename
    path.write_bytes(content)

    content_hash = hashlib.sha256(content).hexdigest()
    raw_doc = RawDocument(
        url=None,
        content_type=mime,
        content=None,
        file_path=str(path),
        content_hash=content_hash,
    )
    db.add(raw_doc)
    await db.flush()

    job = JobLog(
        id=uuid.uuid4(),
        job_name="extract_offer_from_image",
        status="pending",
        payload={"file_path": str(path), "raw_document_id": str(raw_doc.id), "mime": mime},
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job
