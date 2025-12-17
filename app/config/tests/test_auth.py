import uuid
import jwt
import pytest
import pytest_asyncio

from app.config.auth import get_current_user
from app.config.settings import Settings

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.users.models import User
from app.features.users.tests.fixtures import UserFactory


@pytest_asyncio.fixture
async def user_fixture(db_fixture: AsyncSession):
    user: User = UserFactory.build(password__raw="correctpassword")
    db_fixture.add(user)
    await db_fixture.commit()
    await db_fixture.refresh(user)
    return user


@pytest.mark.asyncio
async def test_get_current_user_success(settings_fixture: Settings, db_fixture: AsyncSession, user_fixture: User):
    token = jwt.encode({"sub": str(user_fixture.id)}, settings_fixture.jwt_secret_key, algorithm="HS256")
    result = await get_current_user(token=token, settings=settings_fixture, db=db_fixture)
    assert result == user_fixture


@pytest.mark.asyncio
async def test_get_current_user_invalid_jwt(settings_fixture: Settings, db_fixture: AsyncSession):
    token = "invalid.token.here"
    with pytest.raises(Exception) as exc_info:
        await get_current_user(token=token, settings=settings_fixture, db=db_fixture)
    assert "Could not validate credentials" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_current_user_nonexistent_user(settings_fixture: Settings, db_fixture: AsyncSession):
    token = jwt.encode({"sub": str(uuid.uuid4())}, settings_fixture.jwt_secret_key, algorithm="HS256")
    with pytest.raises(Exception) as exc_info:
        await get_current_user(token=token, settings=settings_fixture, db=db_fixture)
    assert "Could not validate credentials" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_current_user_malformed_user_id(settings_fixture: Settings, db_fixture: AsyncSession):
    token = jwt.encode({"sub": "not-a-uuid"}, settings_fixture.jwt_secret_key, algorithm="HS256")
    with pytest.raises(Exception) as exc_info:
        await get_current_user(token=token, settings=settings_fixture, db=db_fixture)
    assert "Could not validate credentials" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_current_user_missing_user_id(settings_fixture: Settings, db_fixture: AsyncSession):
    token = jwt.encode({}, settings_fixture.jwt_secret_key, algorithm="HS256")
    with pytest.raises(Exception) as exc_info:
        await get_current_user(token=token, settings=settings_fixture, db=db_fixture)
    assert "Could not validate credentials" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_current_user_expired_token(settings_fixture: Settings, db_fixture: AsyncSession):
    import datetime

    expired_time = datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=1)
    token = jwt.encode(
        {"sub": str(uuid.uuid4()), "exp": expired_time}, settings_fixture.jwt_secret_key, algorithm="HS256"
    )
    with pytest.raises(Exception) as exc_info:
        await get_current_user(token=token, settings=settings_fixture, db=db_fixture)
    assert "Could not validate credentials" in str(exc_info.value)
