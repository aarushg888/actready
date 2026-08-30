"""Shared integration DTOs (non-ORM).

These are pure data carriers so adapters stay decoupled from the ORM layer. The
``EvidenceSource`` Protocol's ``fetch()`` yields ``RawEvidence`` instances which
the store layer persists as immutable ``EvidenceArtifact`` rows.
"""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel


class RawEvidence(BaseModel):
    """Normalized evidence returned by an EvidenceSource.fetch()."""

    evidence_type: str  # model_card | eval_run | incident_log | policy
    content: dict[str, object]
    collected_at: dt.date
    source_name: str
