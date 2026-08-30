"""Versioned report snapshot persistence.

Snapshots pin a ``GapReport`` to a ``catalog_version`` (the obligation set it was
scored against) and a ``manifest_hash`` (evidence manifest chain). Together those
guarantee the report reproduces byte-identically later (ISSUES.md M3 exit
criteria; ARCHITECTURE.md invariant 5).

Uses M1's ``app.models_db.ReportSnapshot`` (org-scoped, UUID keys, JSON column).
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Any

from app.models import GapReport
from app.models_db import ReportSnapshot


def save_snapshot(
    report: GapReport,
    catalog_version: str,
    manifest_hash: str,
    *,
    tenant_id: uuid.UUID | str,
    framework_scope: list[str] | None = None,
    db: Any,
) -> ReportSnapshot:
    """Persist a snapshot of ``report`` and return the row (with its id)."""
    row = ReportSnapshot(
        org_id=uuid.UUID(tenant_id) if not isinstance(tenant_id, uuid.UUID) else tenant_id,
        catalog_version=catalog_version,
        manifest_hash=manifest_hash,
        report_json={
            "summary": report.summary,
            "items": [item.model_dump(mode="json") for item in report.items],
            "generated_at": report.generated_at.isoformat(),
        },
        framework_scope=framework_scope or [],
        generated_at=dt.datetime.combine(report.generated_at, dt.time(0, 0)),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def load_snapshot(snapshot_id: uuid.UUID | str, *, db: Any) -> GapReport | None:
    """Reload a snapshot into a ``GapReport`` (or None if not found)."""
    row = db.get(ReportSnapshot, snapshot_id if isinstance(snapshot_id, uuid.UUID) else uuid.UUID(str(snapshot_id)))
    if row is None:
        return None
    data = row.report_json
    return GapReport(
        items=data["items"],
        summary=data["summary"],
        generated_at=dt.date.fromisoformat(data["generated_at"]),
    )


__all__ = ["save_snapshot", "load_snapshot"]
