"""promptfoo / deepeval CI push adapter (INT-2).

Exposes:
  * ``POST /v1/ingest/eval``  - FastAPI router that reuses the EXISTING
    ``app.ingest.parse_eval_run`` parser to normalize the body, then persists an
    ``EvidenceArtifact`` + a ``ControlMapping`` row for the authenticated tenant.
  * ``ingest_eval_file(path, tenant_id)`` - a CLI/path variant for tests and
    automation, exercising the same store path without HTTP.

Auth: M1 owns the principal/tenant resolution and the RLS GUC. This router reads
the tenant id from an ``X-Tenant-Id`` header (or ``tenant_id`` query) so it works
end-to-end today and can be tightened by M1 later without touching the store path.
``set_tenant_context`` is invoked when M1's db module is importable so RLS is
scoped correctly in production; tests inject their own session via
``dependency_overrides`` and skip that seam.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import AsyncSessionLocal, set_tenant_context
from app.ingest import IngestError
from app.integrations.store import finalize_run, ingest_eval_run_json
from app.models_db import IngestionRun


class EvalIngestResponse(BaseModel):
    artifact_id: str
    evidence_type: str
    source_name: str
    mapping_status: str


# --- integration seam: tenant resolution ---------------------------------
def resolve_tenant_id(
    x_tenant_id: Annotated[str | None, Header(alias="X-Tenant-Id")] = None,
    tenant_id: Annotated[str | None, Query(alias="tenant_id")] = None,
) -> uuid.UUID:
    raw = x_tenant_id or tenant_id
    if not raw:
        raise HTTPException(
            status_code=401,
            detail="tenant identity required (X-Tenant-Id header or tenant_id query)",
        )
    try:
        return uuid.UUID(raw)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"invalid tenant id: {raw!r}") from exc


# --- DB session seam (overridden in tests) -------------------------------
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


router = APIRouter(prefix="/v1", tags=["ingest"])


@router.post("/ingest/eval", response_model=EvalIngestResponse)
async def ingest_eval(
    body: dict,
    tenant_id: uuid.UUID = Depends(resolve_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> EvalIngestResponse:
    """Accept promptfoo/deepeval eval JSON pushed from CI; store for the tenant."""
    raw_json = _dump_body(body)
    # Scope the session to the tenant BEFORE any write so RLS (FORCE ROW LEVEL
    # SECURITY) permits the INSERTs below. The GUC is session-scoped (survives
    # commit), so it must be set up front — writing first and setting it after
    # would be rejected by the WITH CHECK policy for a NOBYPASSRLS role.
    await set_tenant_context(session, tenant_id)
    run = IngestionRun(org_id=tenant_id, source="promptfoo_ci", status="running")
    session.add(run)
    await session.flush()
    try:
        artifact = await ingest_eval_run_json(
            session, org_id=tenant_id, eval_json=raw_json, ingestion_run_id=run.id
        )
        # Refresh so the relationship is populated without lazy-loading on a
        # detached/async session (lazy access raises MissingGreenlet in async).
        await session.refresh(artifact, ["mappings"])
        mapping = artifact.mappings[0] if artifact.mappings else None
        await finalize_run(session, run=run, status="success", items=1)
        await session.commit()
    except IngestError as exc:
        await session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - surface as 422, never 500 on bad input
        await session.rollback()
        raise HTTPException(status_code=422, detail=f"eval ingest failed: {exc}") from exc
    return EvalIngestResponse(
        artifact_id=str(artifact.id),
        evidence_type=artifact.evidence_type,
        source_name=artifact.source,
        mapping_status=mapping.status if mapping else "missing",
    )


def _dump_body(body: object) -> str:
    import json

    if isinstance(body, str):
        return body
    return json.dumps(body)


async def ingest_eval_file(
    path: str | Path, tenant_id: str | uuid.UUID, *, session: AsyncSession
) -> uuid.UUID:
    """CLI/path variant: read an eval JSON file and persist it for ``tenant_id``.

    Returns the persisted artifact id. Used by tests and operational scripts.
    """
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    org_id = uuid.UUID(str(tenant_id)) if not isinstance(tenant_id, uuid.UUID) else tenant_id
    # Scope the session to the tenant BEFORE any write (see ingest_eval).
    await set_tenant_context(session, org_id)
    run = IngestionRun(org_id=org_id, source="promptfoo_ci", status="running")
    session.add(run)
    await session.flush()
    artifact = await ingest_eval_run_json(session, org_id=org_id, eval_json=text, ingestion_run_id=run.id)
    await finalize_run(session, run=run, status="success", items=1)
    await session.commit()
    return artifact.id
