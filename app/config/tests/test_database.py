import pytest
from app.config.database import create_db_engine, get_db
from app.config.settings import Settings

from pytest import MonkeyPatch


def test_create_db_engine_is_cached(monkeypatch: MonkeyPatch):
    create_db_engine.cache_clear()

    monkeypatch.setattr("app.config.database.create_async_engine", lambda url, echo: {"url": url, "echo": echo})

    engine_one = create_db_engine("sqlite:///first.db", debug=True)
    engine_two = create_db_engine("sqlite:///first.db", debug=True)
    engine_three = create_db_engine("sqlite:///second.db", debug=False)

    assert engine_one is engine_two
    assert engine_one["echo"] is True
    assert engine_one["url"] == "sqlite:///first.db"
    assert engine_three is not engine_one

    create_db_engine.cache_clear()


@pytest.mark.asyncio
async def test_get_db_provides_session():
    test_settings = Settings.model_construct(database_url="sqlite+aiosqlite:///:memory:", debug=True)
    async with get_db(test_settings) as db:
        assert str(db.bind.url) == "sqlite+aiosqlite:///:memory:"
