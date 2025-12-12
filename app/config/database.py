"""
This module sets up the database connection and session management using SQLAlchemy's async capabilities.
It defines a base class for ORM models and provides a dependency for obtaining database sessions.
The database URL is retrieved from the application settings.
The session maker is provided as a dependency to enable easy access to the database in route handlers.

SQLAlchemy Docs: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html#using-asyncio-scoped-session <br/>
Fast API Docs: https://fastapi.tiangolo.com/tutorial/sql-databases/
"""

from functools import lru_cache
from typing import Annotated
from fastapi import Depends
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.config.settings import SettingsDep

# The base class for ORM models.
# ----------------------------------------------------------------------------------------------------------------------


class Base(DeclarativeBase):
    pass


# Dependency that provides an asynchronous database session.
# The database engine is cached to avoid recreating it on each request.
# ----------------------------------------------------------------------------------------------------------------------


@lru_cache
def create_db_engine(database_url: str, debug: bool = False):
    return create_async_engine(database_url, echo=debug)


async def get_db_session(settings: SettingsDep):
    engine = create_db_engine(settings.database_url, debug=settings.debug)
    session_maker = async_sessionmaker(engine)
    async with session_maker() as session:
        yield session


DbDep = Annotated[AsyncSession, Depends(get_db_session)]
