"""Tests: per-source error isolation (INT-3) + EvidenceSource Protocol.

(a) run_isolated catches a raising source, records a failed IngestionRun, returns [].
"""

from __future__ import annotations

import uuid

import pytest

from app.integrations.base import EvidenceSource, run_isolated
from app.integrations.types import RawEvidence
from app.models_db import IngestionRun


class _BoomSource:
    name = "boom"

    def fetch(self) -> list[RawEvidence]:
        raise RuntimeError("simulated upstream outage")


class _OkSource:
    name = "ok"

    def fetch(self) -> list[RawEvidence]:
        return [
            RawEvidence(
                evidence_type="eval_run",
                content={"cases": []},
                collected_at=__import__("datetime").date.today(),
                source_name="ok:1",
            )
        ]


@pytest.mark.asyncio
async def test_run_isolated_catches_raising_source_and_returns_empty(session, org_id) -> None:
    out = await run_isolated(_BoomSource(), org_id, session)
    assert out == []


@pytest.mark.asyncio
async def test_run_isolated_records_failed_run(session, org_id) -> None:
    await run_isolated(_BoomSource(), org_id, session)
    run = await _latest_run(session, org_id)
    assert run is not None
    assert run.source == "boom"
    assert run.status == "failed"
    assert run.error is not None
    assert "RuntimeError" in run.error
    assert run.finished_at is not None


@pytest.mark.asyncio
async def test_run_isolated_success_records_success_and_items(session, org_id) -> None:
    out = await run_isolated(_OkSource(), org_id, session)
    assert len(out) == 1
    run = await _latest_run(session, org_id)
    assert run is not None
    assert run.status == "success"
    assert run.items_ingested == 1
    assert run.error is None


@pytest.mark.asyncio
async def test_run_isolated_idempotency_key_persisted(session, org_id) -> None:
    key = "run-abc-123"
    await run_isolated(_OkSource(), org_id, session, idempotency_key=key)
    run = await _latest_run(session, org_id)
    assert run is not None
    assert run.idempotency_key == key


@pytest.mark.asyncio
async def test_evidencesource_protocol_is_runtime_checkable() -> None:
    # runtime_checkable Protocol: structural conformance is honored.
    assert isinstance(_OkSource(), EvidenceSource)
    assert not isinstance(object(), EvidenceSource)


async def _latest_run(session, org_id: uuid.UUID) -> IngestionRun | None:
    from sqlalchemy import select

    stmt = select(IngestionRun).where(IngestionRun.org_id == org_id).order_by(IngestionRun.started_at.desc())
    result = await session.execute(stmt)
    return result.scalars().first()
