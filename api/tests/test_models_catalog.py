"""Tests for pydantic domain models and catalog loading."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from app.catalog import load_controls, load_obligations
from app.models import Control, Evidence, GapReport, Obligation

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"


class TestModels:
    def test_evidence_roundtrip(self) -> None:
        e = Evidence(
            type="model_card",
            content={"model_name": "m1"},
            collected_at=dt.date(2026, 8, 1),
        )
        assert e.type == "model_card"
        assert e.content["model_name"] == "m1"

    def test_evidence_bad_type_rejected(self) -> None:
        with pytest.raises(ValueError):
            Evidence(type="blog_post", content={}, collected_at=dt.date(2026, 8, 1))

    def test_control_requires_evidence_types(self) -> None:
        c = Control(id="A.5.1", name="Policy", description="d", evidence_types=["policy"])
        assert c.evidence_types == ["policy"]
        with pytest.raises(ValueError):
            Control(id="A.5.1", name="x", description="d", evidence_types=[])

    def test_obligation_links_controls(self) -> None:
        o = Obligation(
            id="EUAI-ART-11-1",
            article=11,
            title="Technical documentation",
            description="d",
            control_ids=["A.7.2"],
            source_url="https://eur-lex.europa.eu/eli/reg/2024/1689/oj",
        )
        assert o.control_ids == ["A.7.2"]

    def test_gap_report_empty(self) -> None:
        report = GapReport(items=[], summary={})
        assert report.total_count == 0


class TestCatalogLoading:
    def test_loads_35plus_controls(self) -> None:
        controls = load_controls(DATA_DIR)
        assert len(controls) >= 35, f"expected >=35 controls, got {len(controls)}"

    def test_all_control_ids_start_with_A_dot(self) -> None:
        controls = load_controls(DATA_DIR)
        bad = [c.id for c in controls if not c.id.startswith("A.")]
        assert not bad, f"control ids must start 'A.': {bad}"

    def test_every_control_has_evidence_types(self) -> None:
        controls = load_controls(DATA_DIR)
        bad = [c.id for c in controls if not c.evidence_types]
        assert not bad, f"controls missing evidence_types: {bad}"

    def test_control_ids_unique(self) -> None:
        controls = load_controls(DATA_DIR)
        ids = [c.id for c in controls]
        assert len(ids) == len(set(ids)), "duplicate control ids"

    def test_loads_obligations_for_articles_9_to_15(self) -> None:
        obligations = load_obligations(DATA_DIR)
        articles = {o.article for o in obligations}
        assert {9, 10, 11, 12, 13, 14, 15} <= articles

    def test_every_obligation_has_eurlex_source_url(self) -> None:
        obligations = load_obligations(DATA_DIR)
        bad = [o.id for o in obligations if "eur-lex.europa.eu" not in o.source_url]
        assert not bad, f"obligations without eur-lex source_url: {bad}"

    def test_every_obligation_links_at_least_one_control(self) -> None:
        control_ids = {c.id for c in load_controls(DATA_DIR)}
        obligations = load_obligations(DATA_DIR)
        dangling = [
            o.id for o in obligations if not set(o.control_ids) & control_ids
        ]
        assert not dangling, f"obligations with unknown/dangling control_ids: {dangling}"

    def test_missing_field_raises_valueerror(self, tmp_path: Path) -> None:
        (tmp_path / "bad.yaml").write_text(
            "id: A.9.9\ndescription: no name or evidence_types\n", encoding="utf-8"
        )
        with pytest.raises(ValueError):
            load_controls(tmp_path, filename="bad.yaml")

    def test_catalog_files_declare_versions(self) -> None:
        for name in ("controls_iso42001.yaml", "obligations_eu_ai_act.yaml"):
            text = (DATA_DIR / name).read_text(encoding="utf-8")
            assert "version:" in text, f"{name} must declare a version"
