from datetime import datetime, timedelta, timezone
import uuid
from fastapi import HTTPException
import jwt
import pytest
import pytest_asyncio

from app.config.auth import AuthUser
from app.config.auth import Authenticator
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


def test_encode_returns_access_and_refresh_tokens(authenticator_fixture: Authenticator, user_fixture: User):
    access_token, refresh_token = authenticator_fixture.encode(user_fixture)

    assert isinstance(access_token, str)
    assert isinstance(refresh_token, str)


def test_user_decodes_valid_access_token(authenticator_fixture: Authenticator, user_fixture: User):
    access_token, _ = authenticator_fixture.encode(user_fixture)
    auth_user = authenticator_fixture.user(access_token)

    assert isinstance(auth_user, AuthUser)
    assert auth_user.id == user_fixture.id
    assert auth_user.username == user_fixture.username
    assert auth_user.first_name == user_fixture.first_name
    assert auth_user.last_name == user_fixture.last_name


def test_sub_extracts_user_id(authenticator_fixture: Authenticator, user_fixture: User):
    access_token, _ = authenticator_fixture.encode(user_fixture)
    user_id = authenticator_fixture.sub(access_token)

    assert isinstance(user_id, uuid.UUID)
    assert user_id == user_fixture.id


def test_user_invalid_token_raises_401(authenticator_fixture: Authenticator):
    with pytest.raises(HTTPException) as exc:
        authenticator_fixture.user("invalid.token.value")

    assert exc.value.status_code == 401


def test_sub_invalid_token_raises_401(authenticator_fixture: Authenticator):
    with pytest.raises(HTTPException):
        authenticator_fixture.sub("invalid.token.value")


def test_user_missing_user_payload_raises_401(authenticator_fixture: Authenticator, settings_fixture: Settings):
    payload = {"sub": str(uuid.uuid4()), "exp": datetime.now(timezone.utc) + timedelta(minutes=5)}
    token = jwt.encode(payload, settings_fixture.jwt_secret_key, algorithm="HS256")

    with pytest.raises(HTTPException):
        authenticator_fixture.user(token)


def test_user_invalid_user_payload_raises_401(authenticator_fixture: Authenticator, settings_fixture: Settings):
    payload = {
        "sub": str(uuid.uuid4()),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        "user": {"id": "not-a-uuid"},
    }
    token = jwt.encode(payload, settings_fixture.jwt_secret_key, algorithm="HS256")

    with pytest.raises(HTTPException):
        authenticator_fixture.user(token)


def test_sub_missing_sub_claim_raises_401(authenticator_fixture: Authenticator, settings_fixture: Settings):
    payload = {"exp": datetime.now(timezone.utc) + timedelta(minutes=5)}
    token = jwt.encode(payload, settings_fixture.jwt_secret_key, algorithm="HS256")

    with pytest.raises(HTTPException):
        authenticator_fixture.sub(token)


def test_sub_invalid_uuid_raises_401(authenticator_fixture: Authenticator, settings_fixture: Settings):
    payload = {"sub": "not-a-uuid", "exp": datetime.now(timezone.utc) + timedelta(minutes=5)}
    token = jwt.encode(payload, settings_fixture.jwt_secret_key, algorithm="HS256")

    with pytest.raises(HTTPException):
        authenticator_fixture.sub(token)


def test_expired_token_raises_401(authenticator_fixture: Authenticator, settings_fixture: Settings, user_fixture: User):
    payload = {
        "sub": str(user_fixture.id),
        "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        "user": {
            "id": str(user_fixture.id),
            "username": user_fixture.username,
            "first_name": user_fixture.first_name,
            "last_name": user_fixture.last_name,
        },
    }
    expired_token = jwt.encode(payload, settings_fixture.jwt_secret_key, algorithm="HS256")

    with pytest.raises(HTTPException):
        authenticator_fixture.user(expired_token)
