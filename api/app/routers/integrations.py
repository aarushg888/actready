"""Integration health router (INT-3).

``GET /v1/tenant/{id}/integrations`` returns the per-source last status derived
from ``IngestionRun`` rows, so a flaky source is surfaced on a dashboard rather
than 422'ing a report (ARCHITECTURE.md invariant #3).
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import AsyncSessionLocal, set_tenant_context
from app.integrations.base import latest_runs


class SourceStatus(BaseModel):
    source: str
    status: str  # success|partial|failed|running
    last_run_at: object | None
    error: str | None
    items_ingested: int


class TenantIntegrationsResponse(BaseModel):
    tenant_id: str
    sources: list[SourceStatus]


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


router = APIRouter(prefix="/v1", tags=["integrations"])


@router.get("/tenant/{tenant_id}/integrations", response_model=TenantIntegrationsResponse)
async def tenant_integrations(
    tenant_id: str,
    session: AsyncSession = Depends(get_session),
) -> TenantIntegrationsResponse:
    try:
        org_id = uuid.UUID(tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"invalid tenant id: {tenant_id!r}") from exc

    await set_tenant_context(session, org_id)
    runs = await latest_runs(session, org_id)
    sources = [
        SourceStatus(
            source=run.source,
            status=run.status,
            last_run_at=run.finished_at or run.started_at,
            error=run.error,
            items_ingested=run.items_ingested,
        )
        for run in runs.values()
    ]
    sources.sort(key=lambda s: s.source)
    return TenantIntegrationsResponse(tenant_id=tenant_id, sources=sources)
