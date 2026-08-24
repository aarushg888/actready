"""Deterministic evidence -> control -> obligation scoring engine."""

from __future__ import annotations

import datetime as dt
from collections import defaultdict

from app.catalog import DEFAULT_DATA_DIR, load_controls, load_obligations
from app.models import Control, Evidence, GapItem, GapReport

FRESH_DAYS = 180

_HINTS: dict[str, str] = {
    "policy": "Attach an approved policy document covering this control (owner, approval date, review cycle).",
    "model_card": "Attach a model card documenting this system (name, owner, intended use, data summary, evals).",
    "eval_run": "Attach a recent evaluation run (promptfoo/deepeval export) demonstrating this control.",
    "incident_log": "Attach the incident log showing detection, severity and remediation for this control.",
}

_DEFAULT_HINT = "Collect evidence of type {types} dated within the last {days} days."


def _evidence_index(evidence: list[Evidence]) -> dict[str, list[Evidence]]:
    idx: dict[str, list[Evidence]] = defaultdict(list)
    for e in evidence:
        idx[e.type].append(e)
    return idx


def _best_age_days(candidates: list[Evidence], today: dt.date) -> int | None:
    """Age of the freshest evidence among candidates, or None if no candidates."""
    if not candidates:
        return None
    newest = max(c.collected_at for c in candidates)
    return max(0, (today - newest).days)


def map_evidence(
    evidence: list[Evidence],
    controls: list[Control] | None = None,
    today: dt.date | None = None,
) -> GapReport:
    """Score every cataloged control against the provided evidence.

    Deterministic: satisfied iff matching-type evidence exists AND is within FRESH_DAYS;
    partial iff matching-type evidence exists but is stale; missing otherwise.
    Obligations roll up from each control's inbound links.
    """
    controls = controls if controls is not None else load_controls(DEFAULT_DATA_DIR)
    obligations = load_obligations(DEFAULT_DATA_DIR)
    today = today or dt.date.today()

    by_type = _evidence_index(evidence)
    obligations_by_control: dict[str, list[str]] = defaultdict(list)
    for obl in obligations:
        for cid in obl.control_ids:
            obligations_by_control[cid].append(obl.id)

    items: list[GapItem] = []
    for control in controls:
        candidates = [e for t in control.evidence_types for e in by_type.get(t, [])]
        age = _best_age_days(candidates, today)

        if candidates and age is not None and age <= FRESH_DAYS:
            status = "satisfied"
        elif candidates:
            status = "partial"
        else:
            status = "missing"

        if status == "satisfied":
            hint = ""
        elif status == "partial":
            hint = (
                f"Evidence exists but is stale ({age} days old > {FRESH_DAYS}). "
                + _DEFAULT_HINT.format(types="/".join(control.evidence_types), days=FRESH_DAYS)
            )
        else:
            hint = _HINTS.get(control.evidence_types[0], "").format(
                types="/".join(control.evidence_types), days=FRESH_DAYS
            ) or _DEFAULT_HINT.format(
                types="/".join(control.evidence_types), days=FRESH_DAYS
            )

        items.append(
            GapItem(
                control_id=control.id,
                control_name=control.name,
                obligation_ids=sorted(set(obligations_by_control.get(control.id, []))),
                status=status,
                evidence_age_days=age,
                remediation_hint=hint,
            )
        )

    counts: dict[str, int] = {"satisfied": 0, "partial": 0, "missing": 0}
    for item in items:
        counts[item.status] += 1
    total = len(items)
    score = round(100.0 * (counts["satisfied"] + 0.5 * counts["partial"]) / total, 1) if total else 0.0

    summary: dict[str, object] = {
        **counts,
        "total": total,
        "readiness_score": score,
        "as_of": today.isoformat(),
        "freshness_window_days": FRESH_DAYS,
    }
    return GapReport(items=items, summary=summary)
