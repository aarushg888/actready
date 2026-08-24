"""Ingest governance evidence: model cards (YAML), eval runs (JSON), incidents (CSV)."""

from __future__ import annotations

import csv
import datetime as dt
import io
import json
from typing import Any

import yaml

from app.models import Evidence


class IngestError(ValueError):
    """Raised when evidence input is malformed. Message carries the field path."""


_REQUIRED_MODEL_CARD_FIELDS = (
    "model_name",
    "owner",
    "intended_use",
    "training_data_summary",
    "eval_results",
)


def _require_field(data: dict[str, Any], field: str, context: str) -> Any:
    if field not in data or data[field] is None:
        raise IngestError(f"{context}: missing required field '{field}'")
    return data[field]


def parse_model_card(yaml_text: str) -> Evidence:
    """Parse a model card YAML document into an Evidence of type 'model_card'."""
    try:
        doc = yaml.safe_load(yaml_text)
    except yaml.YAMLError as exc:
        raise IngestError(f"model_card: invalid YAML: {exc}") from exc
    if not isinstance(doc, dict):
        raise IngestError("model_card: top-level document must be a mapping")
    for field in _REQUIRED_MODEL_CARD_FIELDS:
        _require_field(doc, field, "model_card")
    collected_at = doc.get("collected_at", dt.date.today())
    if isinstance(collected_at, str):
        try:
            collected_at = dt.date.fromisoformat(collected_at)
        except ValueError as exc:
            raise IngestError(f"model_card: invalid date in 'collected_at': {collected_at!r}") from exc
    return Evidence(
        type="model_card",
        content=doc,
        collected_at=collected_at,
        source_name=str(doc.get("model_name")),
    )


def parse_eval_run(json_text: str) -> Evidence:
    """Normalize promptfoo- or deepeval-shaped eval JSON into an Evidence."""
    try:
        doc = json.loads(json_text)
    except json.JSONDecodeError as exc:
        raise IngestError(f"eval_run: invalid JSON: {exc}") from exc
    if not isinstance(doc, dict):
        raise IngestError("eval_run: top-level JSON must be an object")

    cases: list[dict[str, Any]] = []
    if "results" in doc:  # promptfoo shape
        results = doc["results"]
        if not isinstance(results, list):
            raise IngestError("eval_run: 'results' must be a list (promptfoo shape)")
        for i, row in enumerate(results):
            if not isinstance(row, dict):
                raise IngestError(f"eval_run.results[{i}]: must be an object")
            test_case = row.get("testCase") or {}
            response = row.get("response") or {}
            cases.append(
                {
                    "name": test_case.get("description") or f"case_{i}",
                    "input": test_case.get("vars"),
                    "output": response.get("output"),
                    "passed": bool(row.get("success", False)),
                    "score": row.get("score"),
                    "framework": "promptfoo",
                }
            )
    elif "test_cases" in doc:  # deepeval shape
        rows = doc["test_cases"]
        if not isinstance(rows, list):
            raise IngestError("eval_run: 'test_cases' must be a list (deepeval shape)")
        for i, row in enumerate(rows):
            if not isinstance(row, dict):
                raise IngestError(f"eval_run.test_cases[{i}]: must be an object")
            cases.append(
                {
                    "name": row.get("title") or row.get("name") or f"case_{i}",
                    "metrics": row.get("metrics", []),
                    "passed": all(
                        bool(m.get("success", False)) for m in row.get("metrics", []) if m.get("success") is not None
                    )
                    if row.get("metrics")
                    else bool(row.get("success", False)),
                    "score": None,
                    "framework": "deepeval",
                }
            )
    else:
        raise IngestError(
            "eval_run: unrecognized shape; expected promptfoo {'results': [...]} "
            "or deepeval {'test_cases': [...]}"
        )

    collected_at_raw = doc.get("collected_at", dt.date.today())
    collected_at = (
        dt.date.fromisoformat(collected_at_raw)
        if isinstance(collected_at_raw, str)
        else collected_at_raw
    )
    return Evidence(
        type="eval_run",
        content={"cases": cases, "framework": cases[0]["framework"] if cases else None},
        collected_at=collected_at,
        source_name=str(doc.get("target") or doc.get("subject") or "unknown-target"),
    )


_REQUIRED_INCIDENT_COLUMNS = ("date", "severity", "description", "remediation")


def parse_incidents(csv_text: str) -> list[dict[str, Any]]:
    """Parse an incidents CSV into normalized dicts with ISO dates."""
    reader = csv.DictReader(io.StringIO(csv_text))
    if reader.fieldnames is None:
        raise IngestError("incidents: empty CSV")
    missing = [c for c in _REQUIRED_INCIDENT_COLUMNS if c not in reader.fieldnames]
    if missing:
        raise IngestError(f"incidents: missing required column(s): {', '.join(missing)}")

    events: list[dict[str, Any]] = []
    for lineno, row in enumerate(reader, start=2):  # header is line 1
        raw_date = (row.get("date") or "").strip()
        try:
            parsed_date = dt.date.fromisoformat(raw_date)
        except ValueError as exc:
            raise IngestError(f"incidents line {lineno}: invalid date {raw_date!r}") from exc
        severity = (row.get("severity") or "").strip().lower()
        if severity not in {"critical", "major", "minor"}:
            raise IngestError(
                f"incidents line {lineno}: severity must be critical|major|minor, got {severity!r}"
            )
        events.append(
            {
                "date": parsed_date,
                "severity": severity,
                "description": (row.get("description") or "").strip(),
                "remediation": (row.get("remediation") or "").strip(),
            }
        )
    return events


def parse_incident_log(csv_text: str) -> Evidence:
    """Convenience wrapper: incidents CSV -> Evidence(type='incident_log')."""
    events = parse_incidents(csv_text)
    today = dt.date.today()
    newest = max((e["date"] for e in events), default=today)
    return Evidence(
        type="incident_log",
        content={"events": [e | {"date": e["date"].isoformat()} for e in events]},
        collected_at=newest,
        source_name="incidents.csv",
    )


def collect_evidence(
    model_card_yaml: str | None = None,
    eval_run_json: str | None = None,
    incidents_csv: str | None = None,
) -> list[Evidence]:
    """Ingest any subset of the three evidence kinds into a unified list."""
    out: list[Evidence] = []
    if model_card_yaml:
        out.append(parse_model_card(model_card_yaml))
    if eval_run_json:
        out.append(parse_eval_run(eval_run_json))
    if incidents_csv:
        out.append(parse_incident_log(incidents_csv))
    return out
