"""Pydantic schemas for the ML-assist layer.

These mirror the sketch in docs/planning/ml-plan.md §5. Every extracted field is
confidence-tagged (FieldWithConf) so low-confidence values can be routed to a
human-confirmation queue instead of being trusted automatically.

NOTE: ML outputs are *proposals*. Nothing here is ever written to the
deterministic control_mappings / evidence store unless a human confirms it.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Severity = Literal["low", "med", "high", "critical"]

# Confidence below this is flagged for human review (config, not code — see extract.py).
DEFAULT_REVIEW_THRESHOLD = 0.7


class FieldWithConf(BaseModel):
    """A single extracted field plus a confidence score and review flag.

    `needs_review` is True whenever the confidence falls below the configured
    threshold, signalling that a human must confirm the value before it is
    promoted to real evidence state.
    """

    value: str | None = None
    confidence: float = Field(..., ge=0.0, le=1.0)
    needs_review: bool = Field(
        default=False,
        description="True when confidence < threshold; value must be human-confirmed.",
    )

    @classmethod
    def with_threshold(
        cls, value: str | None, confidence: float, threshold: float = DEFAULT_REVIEW_THRESHOLD
    ) -> FieldWithConf:
        """Build a field, deriving needs_review from confidence vs threshold."""
        return cls(value=value, confidence=confidence, needs_review=confidence < threshold)


# --- Extraction target schemas ------------------------------------------------

class ModelCardFields(BaseModel):
    """Typed fields extracted from a model card (ml-plan §5)."""

    model_name: FieldWithConf
    version: FieldWithConf
    intended_use: FieldWithConf
    eval_metrics: list[FieldWithConf] = Field(default_factory=list)
    data_governance: FieldWithConf | None = None


class IncidentFields(BaseModel):
    """Typed fields extracted from an incident report (ml-plan §5)."""

    incident_date: FieldWithConf
    severity: FieldWithConf  # low|med|high|critical
    affected_article: FieldWithConf | None = None  # e.g. "Art. 73"
    detection_ts: FieldWithConf
    corrective_action: FieldWithConf


class ExtractionResult(BaseModel):
    """Wrapper returned by extract_fields: the populated schema + meta."""

    kind: Literal["model_card", "incident"]
    model_card: ModelCardFields | None = None
    incident: IncidentFields | None = None
    # Count of fields that require human review.
    needs_review_count: int = 0
    provider: str = "none"
    model: str | None = None


# --- Suggestion schema --------------------------------------------------------

class Suggestion(BaseModel):
    """A proposed control/obligation an evidence text bears on.

    Carries similarity, a heuristic confidence, and the grounded source chunk
    so faithfulness is mechanically checkable (RAGAS-style, see classify.py).
    """

    control_id: str
    similarity: float = Field(..., ge=0.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    source_chunk: str = Field(default="", description="Grounded text supporting the suggestion.")
    citation: str = Field(default="", description="Control catalog id + clause reference.")
    control_name: str | None = None
    # faithfulness pre-check result (RAGAS note in classify.py)
    grounded: bool = True


__all__ = [
    "Severity",
    "DEFAULT_REVIEW_THRESHOLD",
    "FieldWithConf",
    "ModelCardFields",
    "IncidentFields",
    "ExtractionResult",
    "Suggestion",
]
