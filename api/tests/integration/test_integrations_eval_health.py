"""Tests: promptfoo/deepeval CI push endpoint (INT-2) and health endpoint (INT-3).

(c) POST /v1/ingest/eval with promptfoo-style JSON persists an EvidenceArtifact
    + ControlMapping for the tenant.
(d) GET /v1/tenant/{id}/integrations returns per-source statuses.

We exercise the route handlers directly via ``await`` (same code path as the HTTP
endpoint, minus the ASGI transport's greenlet spawn) so the persistence contract
is validated deterministically. A lightweight ASGI smoke test confirms the router
is wired and reachable over HTTP.
"""

from __future__ import annotations

import datetime as dt
import json
import uuid
from collections.abc import AsyncGenerator

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.integrations.eval_push import ingest_eval, ingest_eval_file
from app.integrations.types import RawEvidence
from app.main import app  # v0.1 app; M2 routers are included defensively below
from app.models_db import ControlMapping, EvidenceArtifact, Organization
from app.routers.integrations import tenant_integrations


@pytest_asyncio.fixture(loop_scope="function")
async def client(engine, monkeypatch) -> AsyncGenerator[httpx.AsyncClient, None]:
    from app.integrations.eval_push import get_session as eval_get_session
    from app.integrations.eval_push import router as eval_router
    from app.routers.integrations import get_session as integ_get_session
    from app.routers.integrations import router as integrations_router

    app.include_router(eval_router)
    app.include_router(integrations_router)

    async def _override() -> AsyncGenerator[AsyncSession, None]:
        maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False, autoflush=False)
        async with maker() as s:
            yield s

    app.dependency_overrides[eval_get_session] = _override
    app.dependency_overrides[integ_get_session] = _override

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(loop_scope="function")
async def seeded_org(session) -> uuid.UUID:
    # Random slug so back-to-back tests don't collide on organizations.slug
    # (the test DB is shared for the whole session).
    org = Organization(slug=f"ci-tenant-{uuid.uuid4().hex[:8]}", name="CI Tenant")
    session.add(org)
    await session.commit()
    return org.id


PROMPTFOO_BODY = {
    "results": [
        {
            "testCase": {"vars": {"prompt": "refund policy"}},
            "response": {"output": "Refunds within 30 days."},
            "success": True,
            "score": 0.97,
        },
        {
            "testCase": {"vars": {"prompt": "escalation"}},
            "response": {"output": "Escalate to tier-2."},
            "success": False,
            "score": 0.42,
        },
    ]
}


class TestEvalIngestEndpoint:
    async def test_post_eval_persists_artifact_and_mapping(self, session, seeded_org) -> None:
        resp = await ingest_eval(PROMPTFOO_BODY, tenant_id=seeded_org, session=session)
        assert resp.evidence_type == "eval_run"
        assert resp.mapping_status in {"satisfied", "partial"}
        assert uuid.UUID(resp.artifact_id)

        arts = (await session.execute(select(EvidenceArtifact).where(EvidenceArtifact.org_id == seeded_org))).scalars().all()
        assert len(arts) == 1
        maps = (await session.execute(select(ControlMapping).where(ControlMapping.artifact_id == arts[0].id))).scalars().all()
        assert len(maps) == 1
        assert maps[0].control_id.startswith("eval:")

    async def test_post_eval_rejects_bad_json_shape(self, session, seeded_org) -> None:
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            await ingest_eval({"not": "eval-shaped"}, tenant_id=seeded_org, session=session)
        assert exc.value.status_code == 422

    async def test_http_smoke_get_health_reachable(self, client) -> None:
        # Confirm the routers are mounted and the app boots/serves over ASGI.
        resp = await client.get("/openapi.json")
        assert resp.status_code == 200
        paths = resp.json()["paths"]
        assert "/v1/ingest/eval" in paths
        assert "/v1/tenant/{tenant_id}/integrations" in paths


class TestIngestEvalFile:
    async def test_ingest_eval_file_variant(self, session, seeded_org, tmp_path) -> None:
        p = tmp_path / "eval.json"
        p.write_text(json.dumps(PROMPTFOO_BODY))
        aid = await ingest_eval_file(p, seeded_org, session=session)
        assert isinstance(aid, uuid.UUID)
        arts = (await session.execute(select(EvidenceArtifact).where(EvidenceArtifact.org_id == seeded_org))).scalars().all()
        assert len(arts) == 1


class TestHealthEndpoint:
    async def test_health_returns_source_statuses(self, session, seeded_org) -> None:
        from app.integrations.base import run_isolated

        class _Ok:
            name = "promptfoo_ci"

            def fetch(self):
                return [RawEvidence(evidence_type="eval_run", content={}, collected_at=dt.date.today(), source_name="x")]

        class _Boom:
            name = "github_app"

            def fetch(self):
                raise RuntimeError("boom")

        await run_isolated(_Ok(), seeded_org, session)
        await run_isolated(_Boom(), seeded_org, session)

        resp = await tenant_integrations(tenant_id=str(seeded_org), session=session)
        sources = {s.source: s for s in resp.sources}
        assert sources["github_app"].status == "failed"
        assert sources["github_app"].error is not None
        assert sources["promptfoo_ci"].status == "success"
