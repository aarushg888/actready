"""Pydantic domain models for ActReady."""

from __future__ import annotations

import datetime
from typing import ClassVar

from pydantic import BaseModel, Field, field_validator


class Evidence(BaseModel):
    """A single piece of governance evidence."""

    type: str = Field(..., description="e.g. model_card | eval_run | incident_log | policy")
    content: dict[str, object] = Field(default_factory=dict)
    collected_at: datetime.date
    source_name: str | None = None

    ALLOWED_TYPES: ClassVar[frozenset[str]] = frozenset(
        {"model_card", "eval_run", "incident_log", "policy"}
    )

    @field_validator("type")
    @classmethod
    def _validate_type(cls, v: str) -> str:
        if v not in cls.ALLOWED_TYPES:
            raise ValueError(
                f"evidence.type must be one of {sorted(cls.ALLOWED_TYPES)}, got {v!r}"
            )
        return v


class Control(BaseModel):
    """An ISO/IEC 42001 Annex control (condensed)."""

    id: str
    name: str
    description: str
    evidence_types: list[str]

    @field_validator("id", "name", "description")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("control fields must be non-empty")
        return v

    @field_validator("evidence_types")
    @classmethod
    def _has_evidence_types(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("control.evidence_types must be non-empty")
        return v


class Obligation(BaseModel):
    """A legal obligation from the EU AI Act, mapped to controls."""

    id: str
    article: int
    title: str
    description: "str"
    control_ids: list[str]
    source_url: str

    @field_validator("source_url")
    @classmethod
    def _eurlex_url(cls, v: str) -> str:
        if not v.startswith("https://"):
            raise ValueError("obligation.source_url must be an https URL")
        return v


class GapItem(BaseModel):
    """One scored row in a gap report."""

    control_id: str
    control_name: str
    obligation_ids: list[str]
    status: str  # satisfied | partial | missing
    evidence_age_days: int | None
    remediation_hint: str


class GapReport(BaseModel):
    items: list[GapItem]
    summary: dict[str, object]
    generated_at: datetime.date = Field(
        default_factory=datetime.date.today
    )

    @property
    def total_count(self) -> int:
        return len(self.items)
