"""
This module sets up the database connection and session management using SQLAlchemy's async capabilities.
It defines a base class for ORM models and provides a dependency for obtaining database sessions.
The database URL is retrieved from the application settings.
The session maker is provided as a dependency to enable easy access to the database in route handlers.

SQLAlchemy Docs: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html#using-asyncio-scoped-session <br/>
Fast API Docs: https://fastapi.tiangolo.com/tutorial/sql-databases/
"""

from contextlib import asynccontextmanager
from functools import lru_cache
import logging
from typing import Annotated, Iterable
import uuid
from fastapi import Depends
from sqlalchemy import inspect
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import DeclarativeBase, Mapper, RelationshipProperty, attributes
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.util import Properties

from app.config.settings import SettingsDep

logger = logging.getLogger(__name__)

# The base class for ORM models.
# ----------------------------------------------------------------------------------------------------------------------


# noinspection PyPep8Naming
class classproperty(object):
    """
    Helper for defining class property.
    Taken from https://stackoverflow.com/a/13624858
    """

    def __init__(self, fget):
        self.fget = fget

    def __get__(self, owner_self, owner_cls):
        return self.fget(owner_cls)


class Base(DeclarativeBase):
    __abstract__ = True
    id: uuid.UUID

    @classmethod
    @classproperty
    def columns(cls) -> list[str]:
        inspected = inspect(cls)
        assert isinstance(inspected, Mapper)
        return inspected.columns.keys()

    @classmethod
    @classproperty
    def relations(cls) -> list[str]:
        assert isinstance(cls.__mapper__.attrs, Properties)
        return [c.key for c in cls.__mapper__.attrs if isinstance(c, RelationshipProperty)]

    @classmethod
    @classproperty
    def hybrid_properties(cls) -> list[str]:
        inspected = inspect(cls)
        assert isinstance(inspected, Mapper)
        assert isinstance(inspected.all_orm_descriptors, Properties)
        return [item.__name__ for item in inspected.all_orm_descriptors if isinstance(item, hybrid_property)]

    def to_dict(self, nested: bool = False, hybrid_attributes: bool = False, exclude: list[str] | None = None) -> dict:
        """
        Return dict object with model's data.

        Adapted from https://github.com/absent1706/sqlalchemy-mixins/blob/master/sqlalchemy_mixins/serialize.py
        """
        result = dict()

        if exclude is None:
            view_cols = self.columns
        else:
            view_cols = filter(lambda e: e not in exclude, self.columns)

        for key in view_cols:
            result[key] = getattr(self, key)

        if hybrid_attributes:
            for key in self.hybrid_properties:
                result[key] = getattr(self, key)

        if nested:
            for key in self.relations:
                state = attributes.instance_state(self)
                if key in state.unloaded:
                    continue
                obj = getattr(self, key)
                if isinstance(obj, Base):
                    result[key] = obj.to_dict(hybrid_attributes=hybrid_attributes)
                if isinstance(obj, Iterable):
                    result[key] = [o.to_dict(hybrid_attributes=hybrid_attributes) for o in obj if isinstance(o, Base)]

        return result


# Dependency that provides an asynchronous database session.
# The database engine is cached to avoid recreating it on each request.
# ----------------------------------------------------------------------------------------------------------------------


@lru_cache
def create_db_engine(database_url: str, debug: bool = False, is_worker: bool = False):
    logger.info("Creating database engine", extra={"database_url": database_url, "is_worker": is_worker})
    return create_async_engine(database_url, echo=debug)


def create_db_engine_from_settings(settings: SettingsDep):
    return create_db_engine(settings.database_url, debug=settings.debug)


async def get_db_session(settings: SettingsDep):
    engine = create_db_engine_from_settings(settings)
    session_maker = async_sessionmaker(engine)
    async with session_maker() as session:
        yield session


DbDep = Annotated[AsyncSession, Depends(get_db_session)]


# Helper to get a database session within an async context manager.
# This should only be used in places where FastAPI dependencies cannot be used (eg: tasks).
# Make sure the functionality is tested properly when using this.
# ----------------------------------------------------------------------------------------------------------------------


@asynccontextmanager
async def get_db(settings: SettingsDep):
    engine = create_db_engine(settings.database_url, debug=settings.debug, is_worker=True)
    session_maker = async_sessionmaker(engine)
    async with session_maker() as session:
        yield session
