"""
Alembic migration environment configuration.
This file is used by Alembic to run database migrations in both 'online' and 'offline' modes.
It sets up the database connection using the application's settings and logging configuration.

Important: This file
"""

import asyncio
from typing import Any, Literal

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine
from alembic.autogenerate.api import AutogenContext

from alembic import context
import alembic_postgresql_enum  # noqa: F401

from app.config.database import Base
from app.config.logging import setup_logging
from app.config.settings import get_settings
from app.config.timezone import DateTimeUTC

from app.features import models  # noqa: F401


# Run migrations in 'offline' mode
# Generate migrations as SQL scripts, instead of running them against the database.
# Docs: https://alembic.sqlalchemy.org/en/latest/offline.html
# ----------------------------------------------------------------------------------------------------------------------


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_item=render_item,
    )

    with context.begin_transaction():
        context.run_migrations()


# Run migrations in 'online' mode
# Run migrations against the database.
# ----------------------------------------------------------------------------------------------------------------------


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, render_item=render_item)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = config.attributes.get("connection", None)
    if connectable is None:
        connectable = create_async_engine(url=settings.database_url, poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


# Main entry point
# ----------------------------------------------------------------------------------------------------------------------

config = context.config
target_metadata = Base.metadata


def render_item(type_: str, col: Any, autogen_context: AutogenContext) -> str | Literal[False]:
    """Render custom types for autogenerate."""
    if type_ == "type" and isinstance(col, DateTimeUTC):
        return "sa.DateTime(timezone=True)"
    return False


settings = get_settings()
setup_logging(settings)
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
