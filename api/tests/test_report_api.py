"""Tests for markdown rendering and the FastAPI surface."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from fastapi.testclient import TestClient

from app.ingest import collect_evidence
from app.main import app
from app.mapper import map_evidence
from app.models import Evidence
from app.report import render_markdown

FIXTURES = Path(__file__).resolve().parent / "fixtures"


class TestRenderMarkdown:
    def test_contains_scorecard_and_footer(self) -> None:
        report = map_evidence([])
        md = render_markdown(report)
        assert "ISO 42001" in md
        assert "EU AI Act" in md
        assert "eur-lex.europa.eu/eli/reg/2024/1689/oj" in md
        assert "| Control |" in md  # scorecard table header

    def test_worst_first_ordering(self) -> None:
        ev = [Evidence(type="policy", content={}, collected_at=dt.date.today())]
        report = map_evidence(ev)
        md = render_markdown(report)
        # first data row after header separator must be a missing row
        body = [ln for ln in md.splitlines() if ln.startswith("| A.")]
        assert body, "expected table rows"
        assert "missing" in body[0]

    def test_satisfied_rows_appear(self) -> None:
        ev = [
            Evidence(type="policy", content={}, collected_at=dt.date.today()),
            Evidence(type="model_card", content={}, collected_at=dt.date.today()),
            Evidence(type="eval_run", content={}, collected_at=dt.date.today()),
            Evidence(type="incident_log", content={}, collected_at=dt.date.today()),
        ]
        report = map_evidence(ev)
        md = render_markdown(report)
        assert "satisfied" in md


class TestApi:
    def test_healthz(self) -> None:
        client = TestClient(app)
        res = client.get("/healthz")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"

    def test_assess_end_to_end_with_fixtures(self) -> None:
        client = TestClient(app)
        files = [
            ("files", ("model_card.yaml", (FIXTURES / "model_card.yaml").read_bytes(), "application/yaml")),
            ("files", ("promptfoo_run.json", (FIXTURES / "promptfoo_run.json").read_bytes(), "application/json")),
            ("files", ("incidents.csv", (FIXTURES / "incidents.csv").read_bytes(), "text/csv")),
        ]
        res = client.post("/assess", files=files)
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["summary"]["total"] >= 35
        statuses = {i["status"] for i in body["items"]}
        assert "missing" in statuses
        assert "satisfied" in statuses

    def test_assess_rejects_unknown_file_type(self) -> None:
        client = TestClient(app)
        res = client.post(
            "/assess",
            files=[("files", ("notes.txt", b"hello", "text/plain"))],
        )
        assert res.status_code == 422

    def test_assess_empty_upload_is_422(self) -> None:
        client = TestClient(app)
        res = client.post("/assess")
        assert res.status_code == 422


class TestEndToEndMarkdown:
    def test_full_pipeline_text(self) -> None:
        evidence = collect_evidence(
            model_card_yaml=(FIXTURES / "model_card.yaml").read_text(encoding="utf-8"),
            eval_run_json=(FIXTURES / "promptfoo_run.json").read_text(encoding="utf-8"),
            incidents_csv=(FIXTURES / "incidents.csv").read_text(encoding="utf-8"),
        )
        report = map_evidence(evidence)
        md = render_markdown(report)
        assert "ISO 42001" in md
        assert "EU AI Act" in md
        missing_rows = [ln for ln in md.splitlines() if ln.startswith("|") and " missing " in f"{ln} "]
        assert missing_rows, "expected at least one missing row in rendered report"
