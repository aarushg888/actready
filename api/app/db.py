"""Async SQLAlchemy engine + session factory for ActReady.

The default ``DATABASE_URL`` points at the local docker Postgres used in
development. Tests override it via the ``DATABASE_URL`` environment variable
(see ``tests/conftest.py``).
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

DEFAULT_DATABASE_URL = "postgresql+asyncpg://actready:actready@localhost:5432/actready"

DATABASE_URL = os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)

# The RLS GUC that scopes every tenant-scoped query. See migrations/versions/*_rls.py.
TENANT_GUC = "app.tenant_id"


def _make_engine(url: str | None = None):
    """Build the async engine.

    ``pool_pre_ping`` keeps pooled connections honest; ``echo`` stays off so
    logs are not drowned in SQL.
    """
    target = url or DATABASE_URL
    return create_async_engine(target, pool_pre_ping=True, future=True)


engine = _make_engine()

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


def reconfigure(url: str) -> None:
    """Swap the global engine + sessionmaker to a new DATABASE_URL (used by tests).

    Rebuilds ``engine`` and ``AsyncSessionLocal`` so every ``get_session`` /
    service call in the process points at the supplied database. The previous
    engine is intentionally NOT disposed here: disposing a running async engine
    from outside its event loop raises "greenlet is being finalized". It is
    reclaimed by the garbage collector when the old reference is dropped. Tests
    should build the replacement engine inside the *same* event loop they will
    dispose it in (see ``tests/conftest.py`` / ``make_engine``).
    """
    global DATABASE_URL, engine, AsyncSessionLocal
    DATABASE_URL = url
    engine = _make_engine(url)
    AsyncSessionLocal = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )


def set_engine(eng) -> None:
    """Point the globals at an already-built engine (so the caller owns its lifecycle).

    Used by tests that build the engine inside a specific event loop and must
    dispose it within that same loop to avoid the cross-loop greenlet crash.
    """
    global engine, AsyncSessionLocal
    engine = eng
    AsyncSessionLocal = async_sessionmaker(
        eng, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )


def make_engine(url: str | None = None):
    """Public constructor so callers (e.g. tests) can build a disposable engine.

    Build this inside the event loop you intend to dispose it in to avoid the
    cross-loop "greenlet is being finalized" / "Event loop is closed" teardown
    crash that asyncpg raises when an engine's pooled connections outlive their
    event loop.
    """
    return _make_engine(url)


def _dispose_quietly(eng) -> None:
    """Best-effort dispose of an engine even if no loop is running yet."""
    import asyncio

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        return
    if not loop.is_running():
        try:
            loop.run_until_complete(eng.dispose())
        except Exception:
            pass


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding a transactional session."""
    async with AsyncSessionLocal() as session:
        yield session


async def set_tenant_context(session: AsyncSession, tenant_id: object) -> None:
    """Set the session-scoped tenant GUC so RLS policies can read it.

    Uses ``set_config(guc, val, false)`` (the third argument ``is_local=false``),
    which scopes the value to the whole database session/connection and survives
    ``commit()``/``flush()``. This is the correct pattern for RLS: it persists
    across the multiple statements a request issues without being reset on every
    transaction boundary (``SET LOCAL`` would be lost the moment the implicit
    transaction commits, leaking a NULL GUC into later reads).

    The value is always re-asserted by ``get_principal`` (and the integration
    routers) at the start of every request, so a value left on a pooled
    connection is overwritten before any tenant query runs — no cross-tenant
    leak in production.
    """
    await session.execute(
        # Parameterised to avoid SQL injection on the tenant id. is_local=false.
        __import__("sqlalchemy").text("SELECT set_config(:guc, :val, false)"),
        {"guc": TENANT_GUC, "val": str(tenant_id)},
    )
