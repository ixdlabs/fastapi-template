"""
This module sets up the database connection and session management using SQLAlchemy's async capabilities.
It defines a base class for ORM models and provides a dependency for obtaining database sessions.
The database URL is retrieved from the application settings.
The session maker is provided as a dependency to enable easy access to the database in route handlers.

SQLAlchemy Docs: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html#using-asyncio-scoped-session <br/>
Fast API Docs: https://fastapi.tiangolo.com/tutorial/sql-databases/
"""

from collections.abc import Iterable
from typing import Annotated
from functools import lru_cache
import logging
import uuid
from fastapi import Depends
from fast_depends import Depends as WorkerDepends
import orjson
from sqlalchemy import UUID, inspect
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import DeclarativeBase, Mapped, RelationshipProperty, attributes, mapped_column
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool

from app.core.settings import SettingsDep

logger = logging.getLogger(__name__)

# The base class for ORM models.
# ----------------------------------------------------------------------------------------------------------------------


class Base(DeclarativeBase):
    __abstract__ = True
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)

    @classmethod
    def columns(cls) -> list[str]:
        inspected = inspect(cls)
        return inspected.columns.keys()

    @classmethod
    def relations(cls) -> list[str]:
        return [c.key for c in cls.__mapper__.attrs if isinstance(c, RelationshipProperty)]

    @classmethod
    def hybrid_properties(cls) -> list[str]:
        inspected = inspect(cls)
        return [item.__name__ for item in inspected.all_orm_descriptors if isinstance(item, hybrid_property)]

    def to_dict(
        self, nested: bool = False, hybrid_attributes: bool = False, exclude: list[str] | None = None
    ) -> dict[str, object]:
        """
        Return dict object with model's data.

        Adapted from https://github.com/absent1706/sqlalchemy-mixins/blob/master/sqlalchemy_mixins/serialize.py
        """
        result: dict[str, object] = dict()

        if exclude is None:
            view_cols = self.columns()
        else:
            view_cols = filter(lambda e: e not in exclude, self.columns())

        for key in view_cols:
            result[key] = getattr(self, key)

        if hybrid_attributes:
            for key in self.hybrid_properties():
                result[key] = getattr(self, key)

        if nested:
            for key in self.relations():
                state = attributes.instance_state(self)
                if key in state.unloaded:
                    continue
                obj = getattr(self, key)
                if isinstance(obj, Base):
                    result[key] = obj.to_dict(hybrid_attributes=hybrid_attributes)
                if isinstance(obj, Iterable):
                    result[key] = [o.to_dict(hybrid_attributes=hybrid_attributes) for o in obj if isinstance(o, Base)]

        # Convert to standard dict to handle any non-serializable types.
        # Convert any non-serializable types (eg: datetime) to string.
        result = orjson.loads(orjson.dumps(result, default=str))
        return result


# Dependency that provides an asynchronous database session.
# The database engine is cached to avoid recreating it on each request.
# ----------------------------------------------------------------------------------------------------------------------


@lru_cache
def create_db_engine(database_url: str, debug: bool = False, no_pooling: bool = False):
    logger.info("Creating database engine", extra={"database_url": database_url})
    engine_kwargs: dict[str, object] = {"echo": debug}
    # asyncpg connections are bound to their event loop; using NullPool prevents
    # connections created in one loop (e.g., Celery eager tasks) from being reused
    # in another loop (e.g., FastAPI request), which triggers "Future attached to a different loop".
    if no_pooling:
        engine_kwargs["poolclass"] = NullPool
    return create_async_engine(database_url, **engine_kwargs)


def create_db_engine_from_settings(settings: SettingsDep):
    no_pooling = settings.celery_task_always_eager
    return create_db_engine(settings.database_url, debug=settings.debug, no_pooling=no_pooling)


async def get_db_session(settings: SettingsDep):
    engine = create_db_engine_from_settings(settings)
    session_maker = async_sessionmaker(engine)
    async with session_maker() as session:
        yield session


DbDep = Annotated[AsyncSession, Depends(get_db_session)]
DbWorkerDep = Annotated[AsyncSession, WorkerDepends(get_db_session)]
