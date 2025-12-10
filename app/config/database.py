from functools import lru_cache
from typing import Annotated
from fastapi import Depends
from sqlalchemy.orm import DeclarativeBase, Session
from sqlalchemy import create_engine

from app.config.settings import SettingsDep


class Base(DeclarativeBase):
    pass


@lru_cache
def create_db_engine(database_url: str):
    return create_engine(database_url)


def get_db_session(settings: SettingsDep):
    engine = create_db_engine(settings.database_url)
    with Session(engine) as session:
        yield session


DbDep = Annotated[Session, Depends(get_db_session)]
