"""RLS tenant-isolation test (FOUND-2 / E1.3) — the plan's hard exit criterion.

Two orgs insert evidence; an app_user session scoped to org B must NEVER see
org A's rows, even when no application-side WHERE clause is supplied.
"""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import set_tenant_context
from app.db import TENANT_GUC
from app.models_db import EvidenceArtifact


async def test_cross_tenant_read_is_blocked(app_user_session):
    s = app_user_session

    org_a = uuid.uuid4()
    org_b = uuid.uuid4()

    # Seed the orgs themselves (scoped to each org's own GUC so RLS permits insert).
    from app.models_db import Organization

    await set_tenant_context(s, org_a)
    s.add(Organization(id=org_a, slug="org-a", name="Org A"))
    await s.flush()
    await set_tenant_context(s, org_b)
    s.add(Organization(id=org_b, slug="org-b", name="Org B"))
    await s.flush()

    # Insert org A's artifact within org A's tenant context.
    await set_tenant_context(s, org_a)
    art_a = EvidenceArtifact(
        id=uuid.uuid4(),
        org_id=org_a,
        evidence_type="model_card",
        source="test",
        raw_payload={"content": {"x": 1}},
        content_hash="a" * 64,
        collected_at=dt.date(2026, 1, 1),
    )
    s.add(art_a)
    await s.commit()

    # Insert org B's artifact within org B's tenant context.
    await set_tenant_context(s, org_b)
    art_b = EvidenceArtifact(
        id=uuid.uuid4(),
        org_id=org_b,
        evidence_type="model_card",
        source="test",
        raw_payload={"content": {"y": 2}},
        content_hash="b" * 64,
        collected_at=dt.date(2026, 1, 1),
    )
    s.add(art_b)
    await s.commit()

    # --- Switch to org B context; a bare query (no WHERE) must see ONLY org B. ---
    await set_tenant_context(s, org_b)
    rows = (await s.scalars(select(EvidenceArtifact))).all()
    assert len(rows) == 1, f"org B should see exactly 1 row, saw {len(rows)}"
    assert rows[0].org_id == org_b

    # --- Switch to org A context; bare query sees only org A. ---
    await set_tenant_context(s, org_a)
    rows = (await s.scalars(select(EvidenceArtifact))).all()
    assert len(rows) == 1
    assert rows[0].org_id == org_a


async def test_cross_tenant_insert_rejected_by_rls(app_user_session):
    s = app_user_session
    from app.models_db import Organization

    org_a = uuid.uuid4()
    org_b = uuid.uuid4()

    # Seed each org within ITS OWN tenant context (set GUC, then flush that one
    # org). The GUC is session-scoped and survives flush()/commit(), so we must
    # re-assert it before each statement that targets a different tenant.
    await set_tenant_context(s, org_a)
    s.add(Organization(id=org_a, slug="rogue-a", name="A"))
    await s.flush()
    await set_tenant_context(s, org_b)
    s.add(Organization(id=org_b, slug="rogue-b", name="B"))
    await s.flush()

    # Scoped to org A, attempt to insert a row belonging to org B -> WITH CHECK fails.
    await set_tenant_context(s, org_a)
    rogue = EvidenceArtifact(
        id=uuid.uuid4(),
        org_id=org_b,  # different tenant than the active GUC
        evidence_type="model_card",
        source="test",
        raw_payload={"content": {}},
        content_hash="c" * 64,
        collected_at=dt.date(2026, 1, 1),
    )
    s.add(rogue)
    try:
        await s.commit()
    except Exception as exc:  # SQLAlchemy wraps the PG "new row violates row-level security"
        await s.rollback()
        assert "row-level security" in str(exc).lower() or "policy" in str(exc).lower()
    else:  # pragma: no cover - policy should always block
        raise AssertionError("RLS WITH CHECK allowed a cross-tenant insert")


async def test_unset_guc_sees_nothing(app_user_session):
    """With no tenant GUC set, FORCE RLS yields zero visible rows."""
    s = app_user_session
    # Ensure the GUC is unset for this session. We request a brand-new connection
    # from the pool (which has never had the GUC set), so we observe the true
    # "unauthenticated" baseline rather than a value left on a recycled session.
    await s.execute(text(f"SELECT set_config('{TENANT_GUC}', NULL, true)"))
    # Run the read on a dedicated (GUC-clean) connection via a fresh session bound
    # to the same engine, to avoid inheriting a GUC from a previously used pooled
    # connection in this test function.
    from sqlalchemy.ext.asyncio import async_sessionmaker

    maker = async_sessionmaker(app_user_session.bind, class_=AsyncSession, expire_on_commit=False)
    async with maker() as clean:
        rows = (await clean.scalars(select(EvidenceArtifact))).all()
        assert rows == []
