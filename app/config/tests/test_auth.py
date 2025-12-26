from datetime import datetime, timedelta, timezone
import json
import uuid
import jwt
import pytest
import pytest_asyncio
from fastapi.security import SecurityScopes

from app.config.auth import (
    AuthUser,
    AuthException,
    AuthenticationFailedException,
    AuthorizationFailedException,
    get_current_user,
    get_authenticator,
)
from app.config.auth import Authenticator
from app.config.settings import Settings

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.users.models.user import User
from app.fixtures.user_factory import UserFactory


@pytest_asyncio.fixture
async def user_fixture(db_fixture: AsyncSession):
    user: User = UserFactory.build(password__raw="correct_password")
    db_fixture.add(user)
    await db_fixture.commit()
    await db_fixture.refresh(user)
    return user


# Tests for Authenticator
# ----------------------------------------------------------------------------------------------------------------------


def test_get_authenticator_returns_authenticator_instance(settings_fixture: Settings):
    authenticator = get_authenticator(settings_fixture)
    assert isinstance(authenticator, Authenticator)


def test_encode_without_requested_scopes_returns_tokens_with_default_scopes(
    authenticator_fixture: Authenticator, user_fixture: User
):
    access_token, refresh_token = authenticator_fixture.encode(user_fixture)

    assert isinstance(access_token, str)
    assert isinstance(refresh_token, str)
    scopes = authenticator_fixture.scopes(access_token)
    assert scopes == {"user", "customer"}


def test_encode_with_requested_scopes_returns_tokens(authenticator_fixture: Authenticator, user_fixture: User):
    requested_scopes = {"user", "customer"}
    access_token, refresh_token = authenticator_fixture.encode(user_fixture, requested_scopes=requested_scopes)

    assert isinstance(access_token, str)
    assert isinstance(refresh_token, str)
    scopes = authenticator_fixture.scopes(access_token)
    assert scopes == {"user", "customer"}


def test_encode_with_smaller_requested_scopes_returns_tokens(authenticator_fixture: Authenticator, user_fixture: User):
    requested_scopes = {"user"}
    access_token, refresh_token = authenticator_fixture.encode(user_fixture, requested_scopes=requested_scopes)

    assert isinstance(access_token, str)
    assert isinstance(refresh_token, str)
    scopes = authenticator_fixture.scopes(access_token)
    assert scopes == {"user"}


def test_encode_with_non_subset_requested_scopes_raises_auth_exception(
    authenticator_fixture: Authenticator, user_fixture: User
):
    requested_scopes = {"admin", "user"}
    with pytest.raises(AuthException):
        authenticator_fixture.encode(user_fixture, requested_scopes=requested_scopes)


def test_user_decodes_valid_access_token(authenticator_fixture: Authenticator, user_fixture: User):
    access_token, _ = authenticator_fixture.encode(user_fixture)
    auth_user = authenticator_fixture.user(access_token)

    assert isinstance(auth_user, AuthUser)
    assert auth_user.id == user_fixture.id
    assert auth_user.username == user_fixture.username
    assert auth_user.first_name == user_fixture.first_name
    assert auth_user.last_name == user_fixture.last_name


def test_user_fails_with_unknown_token_type(authenticator_fixture: Authenticator, user_fixture: User):
    current_time = datetime.now(timezone.utc)
    expiration = current_time + timedelta(minutes=5)
    payload = {"sub": str(user_fixture.id), "exp": expiration, "type": "unknown_type"}
    token = jwt.encode(payload=payload, key=authenticator_fixture.settings.jwt_secret_key, algorithm="HS256")
    with pytest.raises(AuthException):
        authenticator_fixture.user(token)


def test_sub_extracts_user_id(authenticator_fixture: Authenticator, user_fixture: User):
    access_token, _ = authenticator_fixture.encode(user_fixture)
    user_id = authenticator_fixture.sub(access_token)

    assert isinstance(user_id, uuid.UUID)
    assert user_id == user_fixture.id


def test_user_invalid_token_raises_auth_exception(authenticator_fixture: Authenticator):
    with pytest.raises(AuthException):
        authenticator_fixture.user("invalid.token.value")


def test_sub_invalid_token_raises_auth_exception(authenticator_fixture: Authenticator):
    with pytest.raises(AuthException):
        authenticator_fixture.sub("invalid.token.value")


def test_user_missing_user_payload_raises_auth_exception(
    authenticator_fixture: Authenticator, settings_fixture: Settings
):
    payload = {"sub": str(uuid.uuid4()), "exp": datetime.now(timezone.utc) + timedelta(minutes=5)}
    token = jwt.encode(payload, settings_fixture.jwt_secret_key, algorithm="HS256")

    with pytest.raises(AuthException):
        authenticator_fixture.user(token)


def test_user_invalid_user_payload_raises_auth_exception(
    authenticator_fixture: Authenticator, settings_fixture: Settings
):
    payload = {
        "sub": str(uuid.uuid4()),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        "user": json.dumps({"id": "not-a-uuid"}),
    }
    token = jwt.encode(payload, settings_fixture.jwt_secret_key, algorithm="HS256")

    with pytest.raises(AuthException):
        authenticator_fixture.user(token)


def test_sub_missing_sub_claim_raises_auth_exception(authenticator_fixture: Authenticator, settings_fixture: Settings):
    payload = {"exp": datetime.now(timezone.utc) + timedelta(minutes=5)}
    token = jwt.encode(payload, settings_fixture.jwt_secret_key, algorithm="HS256")

    with pytest.raises(AuthException):
        authenticator_fixture.sub(token)


def test_sub_invalid_uuid_raises_auth_exception(authenticator_fixture: Authenticator, settings_fixture: Settings):
    payload = {"sub": "not-a-uuid", "exp": datetime.now(timezone.utc) + timedelta(minutes=5)}
    token = jwt.encode(payload, settings_fixture.jwt_secret_key, algorithm="HS256")

    with pytest.raises(AuthException):
        authenticator_fixture.sub(token)


def test_expired_token_raises_auth_exception(
    authenticator_fixture: Authenticator, settings_fixture: Settings, user_fixture: User
):
    payload = {
        "sub": str(user_fixture.id),
        "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        "user": json.dumps(
            {
                "id": str(user_fixture.id),
                "username": user_fixture.username,
                "first_name": user_fixture.first_name,
                "last_name": user_fixture.last_name,
            }
        ),
    }
    expired_token = jwt.encode(payload, settings_fixture.jwt_secret_key, algorithm="HS256")

    with pytest.raises(AuthException):
        authenticator_fixture.user(expired_token)


def test_missing_user_payload_raises_auth_exception(
    authenticator_fixture: Authenticator, settings_fixture: Settings, user_fixture: User
):
    payload = {
        "sub": str(user_fixture.id),
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
    }
    token = jwt.encode(payload, settings_fixture.jwt_secret_key, algorithm="HS256")

    with pytest.raises(AuthException):
        authenticator_fixture.user(token)


def test_unexpected_user_payload_raises_auth_exception(
    authenticator_fixture: Authenticator, settings_fixture: Settings, user_fixture: User
):
    payload = {
        "sub": str(user_fixture.id),
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        "user": json.dumps({"unexpected_field": "unexpected_value"}),
    }
    token = jwt.encode(payload, settings_fixture.jwt_secret_key, algorithm="HS256")

    with pytest.raises(AuthException):
        authenticator_fixture.user(token)


def test_user_payload_succeeds(authenticator_fixture: Authenticator, settings_fixture: Settings, user_fixture: User):
    payload = {
        "sub": str(user_fixture.id),
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        "user": json.dumps(
            {
                "id": str(user_fixture.id),
                "username": user_fixture.username,
                "first_name": user_fixture.first_name,
                "last_name": user_fixture.last_name,
            }
        ),
    }
    token = jwt.encode(payload, settings_fixture.jwt_secret_key, algorithm="HS256")

    auth_user = authenticator_fixture.user(token)
    assert isinstance(auth_user, AuthUser)
    assert auth_user.id == user_fixture.id
    assert auth_user.username == user_fixture.username
    assert auth_user.first_name == user_fixture.first_name
    assert auth_user.last_name == user_fixture.last_name


def test_scope_extraction_from_token_with_no_scopes(
    authenticator_fixture: Authenticator, settings_fixture: Settings, user_fixture: User
):
    payload = {
        "sub": str(user_fixture.id),
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
    }
    token = jwt.encode(payload, settings_fixture.jwt_secret_key, algorithm="HS256")

    scopes = authenticator_fixture.scopes(token)
    assert isinstance(scopes, set)
    assert len(scopes) == 0


def test_scope_extraction_from_token_with_scopes(
    authenticator_fixture: Authenticator, settings_fixture: Settings, user_fixture: User
):
    payload = {
        "sub": str(user_fixture.id),
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        "scope": "admin user customer",
    }
    token = jwt.encode(payload, settings_fixture.jwt_secret_key, algorithm="HS256")

    scopes = authenticator_fixture.scopes(token)
    assert isinstance(scopes, set)
    assert scopes == {"admin", "user", "customer"}


def test_scope_extraction_from_token_with_empty_scope(
    authenticator_fixture: Authenticator, settings_fixture: Settings, user_fixture: User
):
    payload = {
        "sub": str(user_fixture.id),
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        "scope": "",
    }
    token = jwt.encode(payload, settings_fixture.jwt_secret_key, algorithm="HS256")

    scopes = authenticator_fixture.scopes(token)
    assert isinstance(scopes, set)
    assert len(scopes) == 0


def test_scope_extraction_from_invalid_token_raises_auth_exception(
    authenticator_fixture: Authenticator,
):
    with pytest.raises(AuthException):
        authenticator_fixture.scopes("invalid.token.value")


# Tests for get_current_user
# ----------------------------------------------------------------------------------------------------------------------


def test_get_current_user_raises_401(authenticator_fixture: Authenticator):
    with pytest.raises(AuthenticationFailedException):
        get_current_user("invalid.token.value", authenticator_fixture)


def test_get_current_user_returns_for_valid_access_token(authenticator_fixture: Authenticator, user_fixture: User):
    access_token, _ = authenticator_fixture.encode(user_fixture)
    user = get_current_user(access_token, authenticator_fixture)

    assert user.id == user_fixture.id
    assert user.username == user_fixture.username
    assert user.first_name == user_fixture.first_name
    assert user.last_name == user_fixture.last_name


def test_get_current_user_returns_for_valid_access_token_with_matching_scopes(
    authenticator_fixture: Authenticator, user_fixture: User
):
    requested_scopes = {"user", "customer"}
    access_token, _ = authenticator_fixture.encode(user_fixture, requested_scopes=requested_scopes)
    user = get_current_user(access_token, authenticator_fixture, security_scopes=SecurityScopes(scopes=["user"]))

    assert user.id == user_fixture.id
    assert user.username == user_fixture.username
    assert user.first_name == user_fixture.first_name
    assert user.last_name == user_fixture.last_name


def test_get_current_user_raises_401_for_valid_access_token_with_non_matching_scopes(
    authenticator_fixture: Authenticator, user_fixture: User
):
    requested_scopes = {"user"}
    access_token, _ = authenticator_fixture.encode(user_fixture, requested_scopes=requested_scopes)
    with pytest.raises(AuthorizationFailedException):
        get_current_user(access_token, authenticator_fixture, security_scopes=SecurityScopes(scopes=["admin"]))


def test_get_current_user_returns_for_valid_access_token_with_no_requested_scopes(
    authenticator_fixture: Authenticator, user_fixture: User
):
    requested_scopes = {"user"}
    access_token, _ = authenticator_fixture.encode(user_fixture, requested_scopes=requested_scopes)
    user = get_current_user(access_token, authenticator_fixture)

    assert user.id == user_fixture.id
    assert user.username == user_fixture.username
    assert user.first_name == user_fixture.first_name
    assert user.last_name == user_fixture.last_name
