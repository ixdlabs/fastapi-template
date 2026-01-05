from unittest.mock import MagicMock
from fastapi import Request
import pytest
from pytest import MonkeyPatch
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.cache import CacheBuilder
from app.core.feature_flags import FeatureFlags, get_feature_flags
from app.core.preferences import get_preferences
from app.core.settings import Settings
from app.fixtures.preference_factory import PreferenceFactory
from aiocache.base import BaseCache


@pytest.fixture
def request_fixture():
    return MagicMock(spec=Request)


@pytest.fixture
def feature_flags_fixture(
    request_fixture: MagicMock, settings_fixture: Settings, db_fixture: AsyncSession, cache_backend_fixture: BaseCache
):
    return get_feature_flags(
        request=request_fixture,
        settings=settings_fixture,
        preferences=get_preferences(
            settings=settings_fixture,
            db=db_fixture,
            cache=CacheBuilder(backend=cache_backend_fixture, request=request_fixture),
        ),
    )


@pytest.mark.asyncio
async def test_enabled_feature_flag_returns_correct_saved_value(
    feature_flags_fixture: FeatureFlags, db_fixture: AsyncSession
):
    feature_flag = PreferenceFactory.build(key="feature_flag.new_ui", value="true")
    db_fixture.add(feature_flag)
    await db_fixture.commit()

    is_enabled = await feature_flags_fixture.enabled("new_ui")
    assert is_enabled is True

    feature_flag_disabled = PreferenceFactory.build(key="feature_flag.old_ui", value="false")
    db_fixture.add(feature_flag_disabled)
    await db_fixture.commit()

    is_disabled = await feature_flags_fixture.enabled("old_ui")
    assert is_disabled is False


@pytest.mark.asyncio
async def test_supported_feature_flag_returns_correct_value(
    feature_flags_fixture: FeatureFlags, request_fixture: MagicMock
):
    request_fixture.headers = {"X-Feature-Flags": "beta_feature, dark_mode"}

    is_supported = await feature_flags_fixture.supported("beta_feature")
    assert is_supported is True

    is_not_supported = await feature_flags_fixture.supported("new_ui")
    assert is_not_supported is False


@pytest.mark.asyncio
async def test_supported_and_enabled_feature_flag_works_correctly(
    feature_flags_fixture: FeatureFlags, db_fixture: AsyncSession, request_fixture: MagicMock
):
    feature_flag = PreferenceFactory.build(key="feature_flag.special_feature", value="true")
    db_fixture.add(feature_flag)
    await db_fixture.commit()

    request_fixture.headers = {"X-Feature-Flags": "special_feature"}

    is_active_and_supported = await feature_flags_fixture.enabled_and_supported("special_feature")
    assert is_active_and_supported is True

    request_fixture.headers = {"X-Feature-Flags": "other_feature"}

    is_not_active_and_supported = await feature_flags_fixture.enabled_and_supported("special_feature")
    assert is_not_active_and_supported is False


@pytest.mark.asyncio
async def test_enabled_feature_flag_defaults_to_false_when_not_set(feature_flags_fixture: FeatureFlags):
    is_enabled = await feature_flags_fixture.enabled("non_existent_flag")
    assert is_enabled is False


@pytest.mark.asyncio
async def test_supported_feature_flag_defaults_to_false_when_not_in_headers(
    feature_flags_fixture: FeatureFlags, request_fixture: MagicMock
):
    request_fixture.headers = {"X-Feature-Flags": "some_other_flag"}

    is_supported = await feature_flags_fixture.supported("non_existent_flag")
    assert is_supported is False


@pytest.mark.asyncio
async def test_enabled_and_supported_feature_flag_defaults_to_false_when_not_set(
    feature_flags_fixture: FeatureFlags, request_fixture: MagicMock
):
    request_fixture.headers = {"X-Feature-Flags": "some_other_flag"}

    is_enabled_and_supported = await feature_flags_fixture.enabled_and_supported("non_existent_flag")
    assert is_enabled_and_supported is False


@pytest.mark.asyncio
async def test_enabled_feature_flag_checks_settings_first(
    feature_flags_fixture: FeatureFlags, settings_fixture: Settings, db_fixture: AsyncSession, monkeypatch: MonkeyPatch
):
    monkeypatch.setattr(settings_fixture, "feature_flags", {"global_feature"})

    is_enabled = await feature_flags_fixture.enabled("global_feature")
    assert is_enabled is True

    feature_flag = PreferenceFactory.build(key="feature_flag.global_feature", value="false")
    db_fixture.add(feature_flag)
    await db_fixture.commit()

    is_still_enabled = await feature_flags_fixture.enabled("global_feature")
    assert is_still_enabled is True
