"""Pydantic schema for an extracted job offer (T-008).

Every key field is nullable: a missing value is stored as ``None`` and never
invented by the extractor. Per-field confidence (high/medium/low) is carried
in ``confiance`` and persisted to ``offers.confidence`` (JSONB).
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class ConfidenceLevel(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class OffreExtraite(BaseModel):
    # Core fields (all nullable - never invented)
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    contract_type: Optional[str] = None
    education: Optional[str] = None
    experience: Optional[str] = None
    sector: Optional[str] = None
    description: Optional[str] = None
    missions: Optional[List[str]] = None
    profile: Optional[List[str]] = None
    benefits: Optional[str] = None
    how_to_apply: Optional[str] = None
    contact_email: Optional[str] = None
    application_url: Optional[str] = None
    deadline: Optional[datetime] = None

    # Classification: is this actually a job posting?
    is_job_posting: bool = True
    not_a_job_reason: Optional[str] = None

    # Per-field confidence: field name -> high/medium/low
    confiance: dict[str, str] = Field(default_factory=dict)

    @field_validator("confiance")
    @classmethod
    def _validate_confiance(cls, v: dict[str, str]) -> dict[str, str]:
        allowed = {c.value for c in ConfidenceLevel}
        for key, val in v.items():
            if val not in allowed:
                raise ValueError(f"invalid confidence level for {key}: {val}")
        return v

    def is_not_a_job_posting(self) -> bool:
        return not self.is_job_posting
