"""Shared persistence helpers for integration adapters (async).

These write ``EvidenceArtifact`` (+ ``ControlMapping``) rows for a tenant and are
deliberately decoupled from M1's auth layer so the M2 work can be built and
tested standalone. They operate on a SQLAlchemy ``AsyncSession`` passed in and use
M1's canonical ORM models from ``app.models_db`` (so we never clobber M1's schema).

Immutability note: artifacts are append-only (a DB trigger enforces no UPDATE/DELETE
in M1's migration). We only ever INSERT here.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.ingest import IngestError, parse_eval_run
from app.integrations.types import RawEvidence
from app.models_db import ControlMapping, EvidenceArtifact, IngestionRun

DEFAULT_CATALOG_VERSION = "v0.1"


def _sha256(value: object) -> str:
    canonical = json.dumps(value, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


async def store_artifact(
    session: AsyncSession,
    *,
    org_id: uuid.UUID,
    raw: RawEvidence,
    ingestion_run_id: uuid.UUID | None = None,
) -> EvidenceArtifact:
    """Persist one RawEvidence as an immutable EvidenceArtifact; return it."""
    payload = {
        "evidence_type": raw.evidence_type,
        "content": raw.content,
        "collected_at": raw.collected_at.isoformat(),
        "source_name": raw.source_name,
    }
    artifact = EvidenceArtifact(
        org_id=org_id,
        evidence_type=raw.evidence_type,
        source=raw.source_name,
        raw_payload=payload,
        content_hash=_sha256(payload),
        collected_at=raw.collected_at,
        ingestion_run_id=ingestion_run_id,
    )
    session.add(artifact)
    await session.flush()
    return artifact


async def store_control_mappings(
    session: AsyncSession,
    *,
    artifact: EvidenceArtifact,
    mappings: list[ControlMapping],
) -> None:
    """Attach pre-built ControlMapping rows to an artifact (no overwrite logic here)."""
    for m in mappings:
        m.artifact_id = artifact.id
        session.add(m)
    await session.flush()


async def ingest_eval_run_json(
    session: AsyncSession,
    *,
    org_id: uuid.UUID,
    eval_json: str,
    source_name: str = "promptfoo_ci",
    ingestion_run_id: uuid.UUID | None = None,
    catalog_version: str = DEFAULT_CATALOG_VERSION,
) -> EvidenceArtifact:
    """Normalize promptfoo/deepeval JSON via the EXISTING parser and store it.

    Reuses ``app.ingest.parse_eval_run`` exactly (INT-2 requirement: zero new
    normalization). Returns the persisted ``EvidenceArtifact``.
    """
    try:
        evidence = parse_eval_run(eval_json)
    except IngestError:
        raise  # surface malformed input to the endpoint caller

    raw = RawEvidence(
        evidence_type=evidence.type,
        content=evidence.content,
        collected_at=evidence.collected_at,
        source_name=str(evidence.source_name or source_name),
    )
    artifact = await store_artifact(session, org_id=org_id, raw=raw, ingestion_run_id=ingestion_run_id)
    # The eval run already carries framework + pass/fail info; record a single
    # umbrella control mapping so the tenant can see it contributed to scoring.
    raw_cases = evidence.content.get("cases")
    cases: list[dict[str, object]] = raw_cases if isinstance(raw_cases, list) else []
    passed = sum(1 for c in cases if c.get("passed"))
    total = len(cases)
    mapping = ControlMapping(
        artifact_id=artifact.id,
        control_id=f"eval:{evidence.content.get('framework')}",
        obligation_id=None,
        status="satisfied" if total and passed == total else "partial",
        score=(passed / total) if total else None,
        catalog_version=catalog_version,
        suggested_by_ml=False,
        confirmed=False,
    )
    await store_control_mappings(session, artifact=artifact, mappings=[mapping])
    return artifact


async def finalize_run(
    session: AsyncSession,
    *,
    run: IngestionRun,
    status: str,
    items: int = 0,
    error: str | None = None,
) -> None:
    run.status = status
    run.items_ingested = items
    run.error = error
    run.finished_at = dt.datetime.utcnow()
    await session.flush()
