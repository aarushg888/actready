"""Integration adapter base: EvidenceSource Protocol + per-source error isolation.

The isolation contract (ISSUES.md INT-3, ARCHITECTURE.md invariant #3): a single
flaky source must NEVER raise into the caller. ``run_isolated`` wraps an
adapter's ``fetch()`` in a blanket try/except, records an ``IngestionRun`` row
with ``status='failed'`` and a truncated ``error`` string, and returns ``[]`` so
the caller can keep processing the remaining sources.

This module is intentionally coordination-light: it imports the ORM models from
M1's ``app.models_db`` and a sync/async session from ``app.db``. It does NOT
define its own models (we prefer M1's canonical tables to avoid clobbering).
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Protocol, runtime_checkable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.types import RawEvidence
from app.models_db import IngestionRun


@runtime_checkable
class EvidenceSource(Protocol):
    """A connector that fetches normalized evidence from one external source."""

    name: str

    def fetch(self) -> list[RawEvidence]:
        """Return normalized evidence. May raise; the isolation wrapper catches it."""
        ...


def _truncate(value: str, limit: int = 500) -> str:
    value = value or ""
    return value if len(value) <= limit else value[: limit - 1] + "\u2026"


async def run_isolated(
    source: EvidenceSource,
    org_id: uuid.UUID,
    session: AsyncSession,
    *,
    idempotency_key: str | None = None,
) -> list[RawEvidence]:
    """Run one source with full isolation (async session).

    On success: persists an ``IngestionRun`` (status='success', item count) and
    returns the evidence. On ANY exception: persists a failed ``IngestionRun``
    (status='failed', truncated error) and returns ``[]``. The caller is never
    allowed to observe an exception from a single source.
    """
    run = IngestionRun(
        org_id=org_id,
        source=getattr(source, "name", "unknown"),
        idempotency_key=idempotency_key,
        status="running",
    )
    session.add(run)
    await session.flush()  # assign run.id so artifacts can reference it

    try:
        evidence = source.fetch()
    except Exception as exc:  # noqa: BLE001 - catch EVERYTHING by design
        run.status = "failed"
        run.error = _truncate(f"{type(exc).__name__}: {exc}")
        run.finished_at = dt.datetime.utcnow()
        await session.commit()
        return []
    else:
        run.status = "success"
        run.items_ingested = len(evidence)
        run.finished_at = dt.datetime.utcnow()
        await session.commit()
        return evidence


async def latest_runs(session: AsyncSession, org_id: uuid.UUID) -> dict[str, IngestionRun]:
    """Return the most recent IngestionRun per source for a tenant (health view)."""
    stmt = (
        select(IngestionRun)
        .where(IngestionRun.org_id == org_id)
        .order_by(IngestionRun.started_at.desc())
    )
    by_source: dict[str, IngestionRun] = {}
    result = await session.execute(stmt)
    for run in result.scalars():
        if run.source not in by_source:
            by_source[run.source] = run
    return by_source
