from unittest.mock import MagicMock
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
import time_machine
from app.core.cache import CacheBuilder
from app.core.preferences import Preferences, get_preferences
from app.core.settings import Settings
from app.fixtures.preference_factory import PreferenceFactory
from aiocache.base import BaseCache


@pytest.fixture
def preference_fixture(settings_fixture: Settings, db_fixture: AsyncSession, cache_backend_fixture: BaseCache):
    return get_preferences(
        settings=settings_fixture, db=db_fixture, cache=CacheBuilder(backend=cache_backend_fixture, request=MagicMock())
    )


@pytest.mark.asyncio
async def test_get_preference(preference_fixture: Preferences, db_fixture: AsyncSession):
    preference = PreferenceFactory.build(key="test_key", value="test_value")
    db_fixture.add(preference)
    await db_fixture.commit()

    value = await preference_fixture.get("test_key")
    assert value == "test_value"

    default_value = await preference_fixture.get("non_existent_key", default="default")
    assert default_value == "default"


@pytest.mark.asyncio
async def test_get_all_preferences(preference_fixture: Preferences, db_fixture: AsyncSession):
    preferences = [
        PreferenceFactory.build(key="pref1", value="value1"),
        PreferenceFactory.build(key="pref2", value="value2"),
    ]
    db_fixture.add_all(preferences)
    await db_fixture.commit()

    all_preferences = await preference_fixture.get_all()
    assert all_preferences["pref1"] == "value1"
    assert all_preferences["pref2"] == "value2"


@pytest.mark.skip(reason="aiocache does not support time manipulation for TTL expiry testing")
@pytest.mark.asyncio
async def test_preferences_caching(preference_fixture: Preferences, db_fixture: AsyncSession):
    preferences = [
        PreferenceFactory.build(key="pref1", value="value1"),
        PreferenceFactory.build(key="pref2", value="value2"),
    ]
    db_fixture.add_all(preferences)
    await db_fixture.commit()

    with time_machine.travel("2024-01-01 12:00:00"):
        # First call should fetch from DB and cache the result
        all_preferences_first_call = await preference_fixture.get_all()
        assert all_preferences_first_call["pref1"] == "value1"
        assert all_preferences_first_call["pref2"] == "value2"

        # Modify the database to see if cache is used
        preference_new = PreferenceFactory.build(key="pref3", value="value3")
        db_fixture.add(preference_new)
        await db_fixture.commit()

        # Second call should return cached result, not reflecting the new addition
        all_preferences_second_call = await preference_fixture.get_all()
        assert "pref3" not in all_preferences_second_call
        assert all_preferences_second_call["pref1"] == "value1"
        assert all_preferences_second_call["pref2"] == "value2"

    with time_machine.travel("2024-01-01 12:06:00"):
        # After cache expiry, the new preference should be reflected
        all_preferences_third_call = await preference_fixture.get_all()
        assert all_preferences_third_call["pref1"] == "value1"
        assert all_preferences_third_call["pref2"] == "value2"
        assert all_preferences_third_call["pref3"] == "value3"
