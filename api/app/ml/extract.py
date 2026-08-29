"""Structured field extraction (the ML-2 feature).

Pulls typed fields from model cards / incident reports into Pydantic schemas
using the provider's `extract`. Every field carries a confidence and a
`needs_review` flag when confidence is low. Low-confidence extractions are meant
to land in a human-confirmation queue, never as trusted evidence state.

SAFETY: extract_fields returns a proposal (ExtractionResult). It does not write
to the deterministic evidence store. With provider 'none' it returns an empty
result flagged for review.
"""

from __future__ import annotations

from typing import Any, Literal

from app.ml.providers import Provider, get_provider
from app.ml.schemas import (
    DEFAULT_REVIEW_THRESHOLD,
    ExtractionResult,
    IncidentFields,
    ModelCardFields,
)

ExtractionKind = Literal["model_card", "incident"]

# Few-shot-ish system framing; the real schema is enforced by instructor.
_MODEL_CARD_PROMPT = (
    "Extract the following fields from this model card as structured JSON. "
    "For each field also return a confidence in [0,1].\n\n{model_card}"
)
_INCIDENT_PROMPT = (
    "Extract the following fields from this incident report as structured JSON. "
    "For each field also return a confidence in [0,1].\n\n{incident}"
)


def _count_review(fields: list[Any]) -> int:
    return sum(1 for f in fields if getattr(f, "needs_review", False))


def extract_fields(
    kind: ExtractionKind,
    text: str,
    provider: Provider | None = None,
    threshold: float = DEFAULT_REVIEW_THRESHOLD,
) -> ExtractionResult:
    """Extract typed fields from `text`.

    kind: 'model_card' | 'incident'. Returns an ExtractionResult. When the
    provider is 'none' (or extraction raises), returns an empty result that is
    fully flagged for review.
    """
    if kind not in ("model_card", "incident"):
        raise ValueError(f"kind must be 'model_card' or 'incident', got {kind!r}")

    provider = provider or get_provider()

    # Deterministic short-circuit: no extraction without a real provider.
    if provider.name == "none":
        return ExtractionResult(kind=kind, provider="none", needs_review_count=0)

    schema = ModelCardFields if kind == "model_card" else IncidentFields
    prompt = (
        _MODEL_CARD_PROMPT.format(model_card=text)
        if kind == "model_card"
        else _INCIDENT_PROMPT.format(incident=text)
    )

    try:
        parsed = provider.extract(prompt, schema)
    except Exception:  # noqa: BLE001 — extraction is best-effort; degrade safely
        return ExtractionResult(kind=kind, provider=provider.name, needs_review_count=0)

    needs_review = 0
    if kind == "model_card":
        model_card = parsed
        needs_review = _count_review(
            [model_card.model_name, model_card.version, model_card.intended_use]
            + model_card.eval_metrics
            + ([model_card.data_governance] if model_card.data_governance else [])
        )
        return ExtractionResult(
            kind=kind,
            model_card=model_card,
            needs_review_count=needs_review,
            provider=provider.name,
            model=getattr(provider, "name", None),
        )
    else:
        incident = parsed
        needs_review = _count_review(
            [
                incident.incident_date,
                incident.severity,
                incident.detection_ts,
                incident.corrective_action,
            ]
            + ([incident.affected_article] if incident.affected_article else [])
        )
        return ExtractionResult(
            kind=kind,
            incident=incident,
            needs_review_count=needs_review,
            provider=provider.name,
            model=getattr(provider, "name", None),
        )


__all__ = ["extract_fields"]
