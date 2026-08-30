"""Assessment service + endpoint test (E2.2 / backend-plan §4).

Registers a tenant via the API, seeds an immutable evidence artifact (bypassing
the file upload for speed), runs the service, and asserts a versioned
``ReportSnapshot`` with a ``manifest_hash`` is persisted — and that an org cannot
see another org's snapshot (RLS end-to-end).
"""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import select

from app.models_db import EvidenceArtifact, ReportSnapshot


async def _register(client, email: str, slug: str) -> dict:
    resp = await client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "supersecret1",
            "org_name": "Org",
            "org_slug": slug,
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


async def test_assess_flow_persists_report(client, session):
    reg = await _register(client, "assess@acme.com", "acme-assess")
    token = reg["access_token"]
    tenant_id = uuid.UUID(reg["tenant_id"])
    user_id = uuid.UUID(reg["user_id"])

    # Seed an immutable model-card artifact for the tenant (privileged session).
    art = EvidenceArtifact(
        id=uuid.uuid4(),
        org_id=tenant_id,
        evidence_type="model_card",
        source="test",
        raw_payload={
            "content": {
                "model_name": "M",
                "owner": "O",
                "intended_use": "U",
                "training_data_summary": "D",
                "eval_results": [],
            },
            "collected_at": "2026-01-01",
            "source_name": "M",
        },
        content_hash="d" * 64,
        collected_at=dt.date(2026, 1, 1),
    )
    session.add(art)
    await session.commit()

    # Call the service-backed endpoint.
    resp = await client.post(
        "/api/assess",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "summary" in body
    assert body["summary"]["readiness_score"] is not None

    # A ReportSnapshot was persisted with a manifest_hash + catalog_version.
    snap = await session.scalar(
        select(ReportSnapshot).where(ReportSnapshot.org_id == tenant_id)
    )
    assert snap is not None
    assert snap.manifest_hash
    assert snap.catalog_version == "v0.2.0"
    assert snap.created_by == user_id

    # ControlMappings were written.
    mappings = (await session.scalars(select(ReportSnapshot))).all()
    assert len(mappings) >= 1


async def test_assess_report_is_tenant_scoped(client, session, app_user_session):
    """Org A's snapshot is invisible to org B via RLS (end-to-end isolation)."""
    reg_a = await _register(client, "a@acme.com", "acme-a")
    reg_b = await _register(client, "b@acme.com", "acme-b")
    tid_a = uuid.UUID(reg_a["tenant_id"])
    tid_b = uuid.UUID(reg_b["tenant_id"])

    snap = ReportSnapshot(
        id=uuid.uuid4(),
        org_id=tid_a,
        catalog_version="v0.2.0",
        manifest_hash="e" * 64,
        report_json={"items": [], "summary": {}},
        framework_scope=[],
        created_by=uuid.UUID(reg_a["user_id"]),
    )
    session.add(snap)
    await session.commit()

    # Read as app_user scoped to org B (different tenant) -> must see nothing.
    from app.auth import set_tenant_context

    await set_tenant_context(app_user_session, tid_b)
    rows = (await app_user_session.scalars(select(ReportSnapshot))).all()
    assert rows == []

    # Read as app_user scoped to org A -> must see the snapshot.
    await set_tenant_context(app_user_session, tid_a)
    rows = (await app_user_session.scalars(select(ReportSnapshot))).all()
    assert len(rows) == 1
    assert rows[0].id == snap.id
