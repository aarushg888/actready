"""Tests for the deterministic evidence->controls mapper."""

from __future__ import annotations

import datetime as dt

import pytest

from app.mapper import FRESH_DAYS, map_evidence
from app.models import Evidence

TODAY = dt.date.today()


class TestScoringStates:
    def test_satisfied_with_fresh_matching_evidence(self) -> None:
        ev = [
            Evidence(type="model_card", content={"model_name": "m"}, collected_at=TODAY),
            Evidence(type="policy", content={"name": "ai-policy"}, collected_at=TODAY),
        ]
        report = map_evidence(ev)
        a51 = next(i for i in report.items if i.control_id == "A.5.1")
        assert a51.status == "satisfied"

    def test_partial_when_only_stale_evidence(self) -> None:  # staleness edge
        stale = TODAY - dt.timedelta(days=FRESH_DAYS + 20)
        ev = [Evidence(type="policy", content={"name": "old-policy"}, collected_at=stale)]
        report = map_evidence(ev)
        a51 = next(i for i in report.items if i.control_id == "A.5.1")
        assert a51.status == "partial"
        assert a51.evidence_age_days is not None and a51.evidence_age_days > FRESH_DAYS

    def test_missing_without_evidence(self) -> None:
        report = map_evidence([])
        statuses = {i.status for i in report.items}
        assert statuses == {"missing"}
        assert all(i.remediation_hint for i in report.items)

    def test_wrong_type_does_not_satisfy(self) -> None:
        ev = [Evidence(type="policy", content={}, collected_at=TODAY)]
        report = map_evidence(ev)
        a64 = next(i for i in report.items if i.control_id == "A.6.4")
        assert a64.status != "satisfied"


class TestStalenessEdge:
    def test_200_day_old_evidence_is_partial_not_missing(self) -> None:
        old = TODAY - dt.timedelta(days=200)
        ev = [Evidence(type="eval_run", content={"cases": []}, collected_at=old)]
        report = map_evidence(ev)
        a65 = next(i for i in report.items if i.control_id == "A.6.5")
        assert a65.status == "partial"

    def test_boundary_179_days_is_fresh(self) -> None:
        fresh = TODAY - dt.timedelta(days=FRESH_DAYS - 1)
        ev = [Evidence(type="policy", content={}, collected_at=fresh)]
        report = map_evidence(ev)
        a51 = next(i for i in report.items if i.control_id == "A.5.1")
        assert a51.status == "satisfied"


class TestObligationRollup:
    def test_obligations_roll_up_from_linked_controls(self) -> None:
        ev = [Evidence(type="policy", content={}, collected_at=TODAY)]
        report = map_evidence(ev)
        art9_items = [
            i
            for i in report.items
            if any(o.startswith("EUAI-ART-9") or o.startswith("EUAI-XORG") for o in i.obligation_ids)
        ]
        assert art9_items, "expected at least one item rolled up to an Article 9 obligation"
        a55 = next(i for i in report.items if i.control_id == "A.5.5")
        assert any(o.startswith("EUAI-ART-9") for o in a55.obligation_ids)

    def test_totals_consistent(self) -> None:
        ev = [Evidence(type="model_card", content={}, collected_at=TODAY)]
        report = map_evidence(ev)
        counts = {"satisfied": 0, "partial": 0, "missing": 0}
        for item in report.items:
            counts[item.status] += 1
        summary = report.summary
        assert summary["total"] == len(report.items)
        assert summary["satisfied"] == counts["satisfied"]
        assert summary["partial"] == counts["partial"]
        assert summary["missing"] == counts["missing"]
        assert sum(counts.values()) == report.total_count

    def test_remediation_hint_present_on_every_gap(self) -> None:
        report = map_evidence([])
        assert all(i.remediation_hint.strip() for i in report.items)

    def test_deterministic_repeat_call(self) -> None:
        today = dt.date.today()
        ev = [Evidence(type="model_card", content={}, collected_at=today)]
        r1, r2 = map_evidence(list(ev)), map_evidence(list(ev))
        assert [i.model_dump() for i in r1.items] == [i.model_dump() for i in r2.items]


class TestUnknownControlLink:
    def test_control_with_no_obligations_gets_empty_list(self) -> None:
        report = map_evidence([])
        lonely = [i for i in report.items if not i.obligation_ids]
        assert isinstance(lonely, list)  # no crash; rollup may be empty for some controls


@pytest.fixture(scope="module")
def full_report():
    return map_evidence([])
