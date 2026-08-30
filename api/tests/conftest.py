"""Pytest fixtures for ActReady v0.2.

A real Postgres test database (``actready_test``) is created/dropped once per
session from the ``DATABASE_URL`` env var (default points at the local docker PG).
Migrations are applied via Alembic so the schema — including RLS — exactly
matches production. The ``app_user`` role (NOBYPASSRLS) is provisioned so the RLS
isolation test exercises a non-superuser connection that the policy actually
filters.
"""

from __future__ import annotations

import datetime as dt
import os
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.main import app
from app.models_db import Base

# Base URL used to derive the test database name.
_DEV_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://actready:actready@localhost:5432/actready",
)
# Swap the database segment for the test database.
_TEST_DB_URL = _DEV_URL.rsplit("/", 1)[0] + "/actready_test"
# A superuser (bypassrls) URL for setup/teardown and privileged ops.
_ADMIN_URL = _TEST_DB_URL

# Runtime role used by the app in production: NOBYPASSRLS, proves RLS.
APP_USER_URL = _TEST_DB_URL.replace("actready:actready", "app_user:app_user")


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def admin_engine():
    """Superuser engine for DB create/drop + migrations (bypasses RLS)."""
    engine = create_async_engine(_ADMIN_URL, pool_pre_ping=True)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def test_database(admin_engine):
    """Create the test database, run migrations, provision app_user. Torn down after."""
    # Connect to the default 'actready' DB to create/drop the test DB.
    base = _DEV_URL.rsplit("/", 1)[0] + "/actready"
    boot = create_async_engine(base, pool_pre_ping=True)
    async with boot.connect() as conn:
        await conn.execution_options(isolation_level="AUTOCOMMIT")
        await conn.execute(text("DROP DATABASE IF EXISTS actready_test"))
        await conn.execute(text("CREATE DATABASE actready_test"))
    await boot.dispose()

    # Run Alembic migrations against the test DB IN-PROCESS (no subprocess, no
    # env-var ambiguity) so CI deterministically builds the schema including RLS.
    from alembic import command
    from alembic.config import Config as AlembicConfig

    api_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    alembic_cfg = AlembicConfig(os.path.join(api_dir, "alembic.ini"))
    alembic_cfg.set_main_option(
        "script_location", os.path.join(api_dir, "migrations")
    )
    # Point the migration explicitly at the TEST database, regardless of any
    # inherited DATABASE_URL in the process environment (this was the CI bug:
    # the old `uv run alembic` subprocess inherited the parent's DATABASE_URL
    # and migrated the wrong database).
    alembic_cfg.set_main_option("sqlalchemy.url", _TEST_DB_URL)

    # Alembic's `command.upgrade` is synchronous — it drives its own event loop
    # internally (env.py calls asyncio.run). Running it inside a dedicated worker
    # thread gives it an isolated loop and avoids both "asyncio.run() cannot be
    # called from a running loop" (pytest-asyncio owns the session loop) and the
    # double-asyncio.run crash. We also point DATABASE_URL at the TEST database
    # for the duration of the upgrade: migrations/env.py reads DATABASE_URL from
    # the environment FIRST, so an inherited DATABASE_URL (e.g. CI's `actready`)
    # would otherwise migrate the wrong DB.
    import os as _os
    import threading

    def _run_migrations() -> None:
        _prev = _os.environ.get("DATABASE_URL")
        _os.environ["DATABASE_URL"] = _TEST_DB_URL
        try:
            command.upgrade(alembic_cfg, "head")
        finally:
            if _prev is None:
                _os.environ.pop("DATABASE_URL", None)
            else:
                _os.environ["DATABASE_URL"] = _prev

    _t = threading.Thread(target=_run_migrations)
    _t.start()
    _t.join()

    # Provision the app_user runtime role + grants (mirrors the RLS migration but
    # idempotent for repeat test runs).
    async with admin_engine.connect() as conn:
        await conn.execution_options(isolation_level="AUTOCOMMIT")
        for stmt in (
            "DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='app_user') "
            "THEN CREATE ROLE app_user LOGIN PASSWORD 'app_user'; END IF; END $$",
            "ALTER ROLE app_user NOBYPASSRLS",
            "GRANT ALL ON DATABASE actready_test TO app_user",
            "GRANT ALL ON SCHEMA public TO app_user",
            "GRANT ALL ON ALL TABLES IN SCHEMA public TO app_user",
            "GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO app_user",
        ):
            await conn.execute(text(stmt))
    yield _TEST_DB_URL
    # Teardown
    boot2 = create_async_engine(base, pool_pre_ping=True)
    async with boot2.connect() as conn:
        await conn.execution_options(isolation_level="AUTOCOMMIT")
        await conn.execute(text("DROP DATABASE IF EXISTS actready_test WITH (FORCE)"))


@pytest_asyncio.fixture
async def session_engine(test_database):
    """Privileged (bypassrls) engine for test setup, per-test (bound to test loop)."""
    engine = create_async_engine(test_database, pool_pre_ping=True)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def app_user_engine(test_database):
    """NOBYPASSRLS engine as app_user, per-test (bound to test loop)."""
    engine = create_async_engine(APP_USER_URL, pool_pre_ping=True)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def app_db(test_database):
    """Point the app's global engine at the test DB, within THIS test's loop.

    The engine is built here (in the function-scoped async fixture's event loop)
    and disposed here too, so the asyncio engine lifecycle never crosses an event
    loop boundary — disposing an async engine from a *different* loop is exactly
    what raises "greenlet is being finalized" / "Event loop is closed" in
    teardown. The import-time global engine is left untouched (GC-reclaimed).
    """
    from app.db import make_engine, set_engine

    eng = make_engine(test_database)
    set_engine(eng)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session(session_engine):
    """A privileged (bypassrls) session for test setup, scoped per test."""
    maker = async_sessionmaker(session_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        yield s


@pytest_asyncio.fixture
async def app_user_session(app_user_engine):
    """A NOBYPASSRLS session as app_user — the role that RLS actually filters."""
    maker = async_sessionmaker(app_user_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        yield s


@pytest_asyncio.fixture
async def client(app_db):
    """httpx AsyncClient bound to the ASGI app (test DB, bypassrls)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def make_org(session: AsyncSession, name: str = "Acme", slug: str | None = None) -> uuid.UUID:
    """Insert an org and return its id (privileged session)."""
    from app.models_db import Organization

    org = Organization(name=name, slug=slug or f"org-{uuid.uuid4().hex[:8]}")
    session.add(org)
    await session.flush()
    return org.id


# --- Reporting (M3) fixtures: synchronous, in-memory, DB-agnostic ---------------
# These deliberately avoid the async `session`/`engine` fixtures above so the
# reporting tests run standalone (create tables via Base.metadata.create_all on
# SQLite) and do not require the docker Postgres used by M1's RLS suite.
from app.models import Evidence, GapItem, GapReport  # noqa: E402


def _make_report() -> GapReport:
    return GapReport(
        items=[
            GapItem(
                control_id="A.1",
                control_name="AI policy",
                obligation_ids=["OBL-9"],
                status="satisfied",
                evidence_age_days=12,
                remediation_hint="",
            ),
            GapItem(
                control_id="A.2",
                control_name="Risk management",
                obligation_ids=["OBL-9", "OBL-10"],
                status="partial",
                evidence_age_days=40,
                remediation_hint="Add incident retention policy",
            ),
            GapItem(
                control_id="A.7",
                control_name="Data governance",
                obligation_ids=["OBL-10"],
                status="missing",
                evidence_age_days=None,
                remediation_hint="Collect dataset cards",
            ),
        ],
        summary={
            "readiness_score": 55,
            "as_of": "2026-08-29",
            "freshness_window_days": 180,
            "total": 3,
            "satisfied": 1,
            "partial": 1,
            "missing": 1,
        },
        generated_at=dt.date(2026, 8, 29),
    )


def _make_evidence() -> list[Evidence]:
    return [
        Evidence(type="policy", content={}, collected_at=dt.date.today()),
        Evidence(type="model_card", content={}, collected_at=dt.date.today()),
    ]


@pytest.fixture
def report() -> GapReport:
    return _make_report()


@pytest.fixture
def evidence() -> list[Evidence]:
    return _make_evidence()


@pytest.fixture
def sync_engine():
    """In-memory SQLite engine with all reporting tables created.

    Uses ``StaticPool`` so every Session/connection shares ONE in-memory DB
    (otherwise ``sqlite://`` gives each connection a private, empty database).
    """
    from sqlalchemy import create_engine
    from sqlalchemy.pool import StaticPool

    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture
def db_session(sync_engine):
    """A synchronous SQLAlchemy Session bound to the in-memory engine."""
    from sqlalchemy.orm import Session

    with Session(sync_engine) as s:
        yield s
