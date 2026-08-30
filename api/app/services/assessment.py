"""Tenant-aware assessment service (E2.2 / backend-plan §4).

Loads an org's immutable ``EvidenceArtifact`` rows (RLS-scoped automatically),
reconstructs the engine's ``Evidence`` pydantic objects, runs the UNCHANGED
deterministic ``map_evidence`` and persists the result as ``ControlMapping`` rows
plus a versioned ``ReportSnapshot`` with a tamper-evident ``manifest_hash``.

The deterministic engine is the system of record; this layer never passes
``org_id`` into ``map_evidence`` and never mutates control status itself.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.mapper import map_evidence
from app.models import Evidence
from app.models_db import ControlMapping, EvidenceArtifact, ReportSnapshot

# Catalog version pin (FOUND-4 / E2.3). Single source of truth for "which
# obligation set produced this report". Dates live in the catalog data, not code.
CATALOG_VERSION = "v0.2.0"


def _reconstruct_evidence(artifact: EvidenceArtifact) -> Evidence:
    """Turn a stored artifact back into the engine's canonical Evidence type."""
    payload = dict(artifact.raw_payload)
    collected_at = payload.get("collected_at")
    if isinstance(collected_at, str):
        collected_at = dt.date.fromisoformat(collected_at)
    else:
        collected_at = dt.date.today()
    return Evidence(
        type=artifact.evidence_type,
        content=payload.get("content", payload),
        collected_at=collected_at,
        source_name=payload.get("source_name", artifact.source),
    )


def _manifest_hash(artifacts: list[EvidenceArtifact]) -> str:
    """sha256 over the sorted set of artifact content_hashes (hash-chained)."""
    sorted_hashes = sorted(a.content_hash for a in artifacts)
    return hashlib.sha256("\n".join(sorted_hashes).encode("utf-8")).hexdigest()


class AssessmentService:
    """Stateless service bound to a request session (and its tenant context)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def load_evidence(self, tenant_id: uuid.UUID) -> list[EvidenceArtifact]:
        """All artifacts for the tenant. RLS scopes the query; we keep the explicit
        filter for clarity and deterministic behaviour across roles."""
        rows = await self.session.scalars(
            select(EvidenceArtifact).where(EvidenceArtifact.org_id == tenant_id)
        )
        return list(rows)

    async def assess(
        self,
        tenant_id: uuid.UUID,
        created_by: uuid.UUID | None = None,
        today: dt.date | None = None,
    ) -> ReportSnapshot:
        """Run the engine over the tenant's evidence and persist the report.

        Returns the stored ``ReportSnapshot`` (with manifest_hash + catalog_version).
        Deterministic: given the same stored artifacts, the report is reproducible.
        """
        artifacts = await self.load_evidence(tenant_id)
        evidence = [_reconstruct_evidence(a) for a in artifacts]

        report = map_evidence(evidence, today=today)  # pure, unchanged engine

        manifest = _manifest_hash(artifacts)

        # Replace prior mappings that derived from these artifacts for the same
        # catalog version (idempotent re-run).
        artifact_ids = [a.id for a in artifacts]
        if artifact_ids:
            await self.session.execute(
                delete(ControlMapping).where(
                    ControlMapping.catalog_version == CATALOG_VERSION,
                    ControlMapping.artifact_id.in_(artifact_ids),
                )
            )

        # Attach each report item to one of the tenant's artifacts (round-robin).
        # The engine is the system of record; this linkage is for traceability.
        # Skip entirely when the tenant has no artifacts (no valid FK to point at).
        if artifact_ids:
            per_artifact = artifact_ids
            for i, item in enumerate(report.items):
                self.session.add(
                    ControlMapping(
                        artifact_id=per_artifact[i % len(per_artifact)],
                        control_id=item.control_id,
                        obligation_id=item.obligation_ids[0] if item.obligation_ids else None,
                        status=item.status,
                        catalog_version=CATALOG_VERSION,
                    )
                )
        else:
            # Nothing to link; the report (all-missing) is still persisted below.
            pass

        snapshot = ReportSnapshot(
            org_id=tenant_id,
            catalog_version=CATALOG_VERSION,
            manifest_hash=manifest,
            report_json=report.model_dump(mode="json"),
            framework_scope=[],
            created_by=created_by,
        )
        self.session.add(snapshot)
        await self.session.commit()
        await self.session.refresh(snapshot)
        return snapshot


def build_service(session: AsyncSession) -> AssessmentService:
    return AssessmentService(session)
