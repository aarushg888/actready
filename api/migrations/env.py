"""Alembic environment for ActReady (async SQLAlchemy 2.0).

Reads ``DATABASE_URL`` from the environment (default to the dev Postgres) and
runs migrations against the async engine. ``app.models_db.Base.metadata`` is
the source of truth for autogenerate.
"""

from __future__ import annotations

import asyncio
import os

from alembic import context
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy.pool import NullPool

from app.models_db import Base

config = context.config

# Allow the URL to be supplied via env (tests/CI set DATABASE_URL).
database_url = os.environ.get("DATABASE_URL") or config.get_main_option("sqlalchemy.url") or ""
config.set_main_option("sqlalchemy.url", database_url)

target_metadata = Base.metadata


def _run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        render_as_batch=False,
    )
    with context.begin_transaction():
        context.run_migrations()


async def _run_async() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(_run_async())


def run_migrations_offline() -> None:
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        compare_server_default=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
