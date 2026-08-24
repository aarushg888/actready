"""Tests for evidence ingestion: model cards, eval runs, incidents CSV."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pytest

from app.ingest import IngestError, parse_eval_run, parse_incidents, parse_model_card

FIXTURES = Path(__file__).resolve().parent / "fixtures"

MODEL_CARD_YAML = """\
model_name: support-triage-alpha
owner: acme-ai-platform
intended_use: Route inbound support tickets to queues.
training_data_summary: 2 years of anonymized ticket transcripts (~1.2M).
eval_results:
  accuracy: 0.91
"""

PROMPTFOO_JSON = {
    "results": [
        {
            "testCase": {"vars": {"prompt": "refund policy question"}},
            "response": {"output": "Refunds within 30 days."},
            "success": True,
            "score": 0.97,
        },
        {
            "testCase": {"vars": {"prompt": "escalation path"}},
            "response": {"output": "Escalate to tier-2."},
            "success": False,
            "score": 0.42,
        },
    ]
}

DEEPEVAL_JSON = {
    "test_cases": [
        {
            "title": "hallucination check",
            "metrics": [
                {"name": "HallucinationMetric", "score": 0.05, "success": True},
                {"name": "AnswerRelevancyMetric", "score": 0.88, "success": True},
            ],
        }
    ]
}

INCIDENTS_CSV = """date,severity,description,remediation
2026-07-02,major,Wrong refund amount quoted to customer,Prompt updated and regression test added
2026-06-15,minor,Latency spike on EU endpoint,Autoscaling policy adjusted
"""


class TestModelCard:
    def test_happy_path(self) -> None:
        ev = parse_model_card(MODEL_CARD_YAML)
        assert ev.type == "model_card"
        assert ev.content["model_name"] == "support-triage-alpha"
        assert ev.content["eval_results"] == {"accuracy": 0.91}
        assert isinstance(ev.collected_at, dt.date)

    def test_missing_required_field_raises_with_path(self) -> None:
        bad = MODEL_CARD_YAML.replace("owner: acme-ai-platform\n", "")
        with pytest.raises(IngestError) as excinfo:
            parse_model_card(bad)
        assert "owner" in str(excinfo.value)


class TestEvalRun:
    def test_promptfoo_shape(self) -> None:
        ev = parse_eval_run(json.dumps(PROMPTFOO_JSON))
        assert ev.type == "eval_run"
        cases = ev.content["cases"]
        assert isinstance(cases, list) and len(cases) == 2
        first: dict[str, object] = cases[0]  # type: ignore[assignment]
        assert first["passed"] is True

    def test_deepeval_shape(self) -> None:
        ev = parse_eval_run(json.dumps(DEEPEVAL_JSON))
        assert ev.type == "eval_run"
        cases = ev.content["cases"]
        assert isinstance(cases, list)
        first: dict[str, object] = cases[0]  # type: ignore[assignment]
        assert first["name"] == "hallucination check"

    def test_invalid_json_raises(self) -> None:
        with pytest.raises(IngestError):
            parse_eval_run("{not json")

    def test_unrecognized_shape_raises(self) -> None:
        with pytest.raises(IngestError) as excinfo:
            parse_eval_run(json.dumps({"something": "else"}))
        assert "results" in str(excinfo.value) or "test_cases" in str(excinfo.value)


class TestIncidents:
    def test_happy_path(self) -> None:
        events = parse_incidents(INCIDENTS_CSV)
        assert len(events) == 2
        first = events[0]
        assert first["date"] == dt.date(2026, 7, 2)
        assert first["severity"] == "major"
        assert "remediation" in first

    def test_missing_column_raises_with_path(self) -> None:
        bad = INCIDENTS_CSV.replace(",remediation", "")
        with pytest.raises(IngestError) as excinfo:
            parse_incidents(bad)
        assert "remediation" in str(excinfo.value)

    def test_bad_date_raises(self) -> None:
        bad = INCIDENTS_CSV.replace("2026-07-02", "not-a-date")
        with pytest.raises(IngestError) as excinfo:
            parse_incidents(bad)
        assert "date" in str(excinfo.value).lower()


class TestFixtures:
    def test_fixture_files_parse(self) -> None:
        card = parse_model_card((FIXTURES / "model_card.yaml").read_text(encoding="utf-8"))
        run = parse_eval_run((FIXTURES / "promptfoo_run.json").read_text(encoding="utf-8"))
        events = parse_incidents((FIXTURES / "incidents.csv").read_text(encoding="utf-8"))
        assert card.content["model_name"]
        assert run.content["cases"]
        assert events
