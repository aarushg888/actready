"""Pytest fixtures for the M2 integrations suite.

These create the integration tables on a dedicated ``actready_test`` database
(independent of M1's main migrations) so the M2 tests pass on their own even
before M1's alembic migrations exist. We build the schema from M1's canonical
``app.models_db.Base.metadata`` (preferred over a duplicate), which already
defines ``organizations``, ``evidence_artifacts``, ``control_mappings`` and
``ingestion_runs``.

The async engine uses asyncpg (same driver M1's app.db uses).
"""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncGenerator

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Point M1's db module at the test database so its AsyncSessionLocal (if imported)
# and our fixtures agree. Tests override the session directly, but this keeps
# environment consistent.
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://actready:actready@localhost:5432/actready_test"
)

from app.models_db import Organization  # noqa: E402

TEST_DATABASE_URL = os.environ["DATABASE_URL"]


@pytest_asyncio.fixture(loop_scope="function")
async def engine(test_database) -> AsyncGenerator:
    """Engine bound to the migration-applied ``actready_test`` database.

    The schema (including RLS) is owned by the session-scoped ``test_database``
    fixture from the parent ``tests/conftest.py`` (it runs Alembic once). We used
    to ``create_all``/``drop_all`` here, but that wiped the *migration-applied*
    schema — including the RLS policies — and broke every other suite that shares
    ``actready_test``. Now we just open an engine against the already-migrated DB.
    """
    eng = create_async_engine(TEST_DATABASE_URL, pool_pre_ping=True, future=True)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture(loop_scope="function")
async def session(engine, test_database) -> AsyncGenerator[AsyncSession, None]:
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False, autoflush=False)
    async with maker() as s:
        yield s


@pytest_asyncio.fixture(loop_scope="function")
async def org_id(session) -> uuid.UUID:
    """A tenant row the FK columns reference.

    The slug is randomized so consecutive tests in the same session don't collide
    on the unique ``organizations.slug`` constraint (the test DB is shared across
    the whole session and is rebuilt only once, by ``test_database``).
    """
    org = Organization(slug=f"test-tenant-{uuid.uuid4().hex[:8]}", name="Test Tenant")
    session.add(org)
    await session.commit()
    return org.id
