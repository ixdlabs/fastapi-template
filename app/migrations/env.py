"""
Alembic migration environment configuration.
This file is used by Alembic to run database migrations in both 'online' and 'offline' modes.
It sets up the database connection using the application's settings and logging configuration.

Important: This file
"""

import asyncio

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context

from app.config.database import Base
from app.config.logging import setup_logging
from app.config.settings import get_settings


# Import all models here to ensure they are registered with Alembic's metadata.
# This is required for Alembic to detect schema changes.
# ----------------------------------------------------------------------------------------------------------------------

from app.features.users.models import User  # noqa: F401


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
    )

    with context.begin_transaction():
        context.run_migrations()


# Run migrations in 'online' mode
# Run migrations against the database.
# ----------------------------------------------------------------------------------------------------------------------


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
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

settings = get_settings()
setup_logging(settings.migration_logger_name)
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
