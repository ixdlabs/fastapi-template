from functools import lru_cache
from typing import Annotated
from fastapi import Depends
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.config.settings import SettingsDep


class Base(DeclarativeBase):
    pass


@lru_cache
def create_db_engine(database_url: str):
    return create_async_engine(database_url, echo=True)


async def get_db_session_maker(settings: SettingsDep):
    engine = create_db_engine(settings.database_url)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    async with session_maker() as session:
        yield session


DbDep = Annotated[AsyncSession, Depends(get_db_session_maker)]
