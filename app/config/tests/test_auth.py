from datetime import datetime, timedelta, timezone
import json
import uuid
import jwt
import pytest
import pytest_asyncio
from fastapi.security import SecurityScopes
import time_machine

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


def test_get_authenticator_returns_authenticator_configured_with_settings(settings_fixture: Settings):
    authenticator = get_authenticator(settings_fixture)
    assert isinstance(authenticator, Authenticator)


# JWT Encode Tests
# ----------------------------------------------------------------------------------------------------------------------


def test_encode_defaults_to_user_and_customer_scopes_when_none_requested(
    authenticator_fixture: Authenticator, user_fixture: User
):
    access_token, refresh_token = authenticator_fixture.encode(user_fixture)

    assert isinstance(access_token, str)
    assert isinstance(refresh_token, str)
    scopes = authenticator_fixture.scopes(access_token)
    assert scopes == {"user", "customer"}


def test_encode_uses_requested_scopes_when_they_match_allowed_set(
    authenticator_fixture: Authenticator, user_fixture: User
):
    requested_scopes = {"user", "customer"}
    access_token, refresh_token = authenticator_fixture.encode(user_fixture, requested_scopes=requested_scopes)

    assert isinstance(access_token, str)
    assert isinstance(refresh_token, str)
    scopes = authenticator_fixture.scopes(access_token)
    assert scopes == {"user", "customer"}


def test_encode_accepts_subset_of_default_scopes(authenticator_fixture: Authenticator, user_fixture: User):
    requested_scopes = {"user"}
    access_token, refresh_token = authenticator_fixture.encode(user_fixture, requested_scopes=requested_scopes)

    assert isinstance(access_token, str)
    assert isinstance(refresh_token, str)
    scopes = authenticator_fixture.scopes(access_token)
    assert scopes == {"user"}


def test_encode_rejects_requested_scopes_outside_default_set(authenticator_fixture: Authenticator, user_fixture: User):
    requested_scopes = {"admin", "user"}
    with pytest.raises(AuthException):
        authenticator_fixture.encode(user_fixture, requested_scopes=requested_scopes)


# JWT User Tests
# ----------------------------------------------------------------------------------------------------------------------


def test_user_parses_valid_access_token_into_auth_user_model(authenticator_fixture: Authenticator, user_fixture: User):
    access_token, _ = authenticator_fixture.encode(user_fixture)
    auth_user = authenticator_fixture.user(access_token)

    assert isinstance(auth_user, AuthUser)
    assert auth_user.id == user_fixture.id
    assert auth_user.username == user_fixture.username
    assert auth_user.first_name == user_fixture.first_name
    assert auth_user.last_name == user_fixture.last_name


def test_user_raises_auth_exception_for_unknown_token_type(authenticator_fixture: Authenticator, user_fixture: User):
    current_time = datetime.now(timezone.utc)
    expiration = current_time + timedelta(minutes=5)
    payload = {"sub": str(user_fixture.id), "exp": expiration, "type": "unknown_type"}
    token = jwt.encode(payload=payload, key=authenticator_fixture.settings.jwt_secret_key, algorithm="HS256")
    with pytest.raises(AuthException):
        authenticator_fixture.user(token)


def test_user_raises_auth_exception_for_malformed_jwt(authenticator_fixture: Authenticator):
    with pytest.raises(AuthException):
        authenticator_fixture.user("invalid.token.value")


def test_user_raises_auth_exception_when_user_payload_missing(
    authenticator_fixture: Authenticator, settings_fixture: Settings
):
    payload = {"sub": str(uuid.uuid4()), "exp": datetime.now(timezone.utc) + timedelta(minutes=5)}
    token = jwt.encode(payload, settings_fixture.jwt_secret_key, algorithm="HS256")

    with pytest.raises(AuthException):
        authenticator_fixture.user(token)


def test_user_raises_auth_exception_for_invalid_user_payload(
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


def test_user_raises_auth_exception_for_expired_token(
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


def test_user_raises_auth_exception_when_user_payload_not_provided(
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


def test_user_raises_auth_exception_for_unexpected_payload_fields(
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


def test_user_returns_auth_user_when_payload_contains_expected_fields(
    authenticator_fixture: Authenticator, settings_fixture: Settings, user_fixture: User
):
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


# JWT sub Tests
# ----------------------------------------------------------------------------------------------------------------------


def test_sub_raises_auth_exception_for_malformed_jwt(authenticator_fixture: Authenticator):
    with pytest.raises(AuthException):
        authenticator_fixture.sub("invalid.token.value")


def test_sub_returns_uuid_from_access_token(authenticator_fixture: Authenticator, user_fixture: User):
    access_token, _ = authenticator_fixture.encode(user_fixture)
    user_id = authenticator_fixture.sub(access_token)

    assert isinstance(user_id, uuid.UUID)
    assert user_id == user_fixture.id


def test_sub_raises_auth_exception_when_sub_claim_missing(
    authenticator_fixture: Authenticator, settings_fixture: Settings
):
    payload = {"exp": datetime.now(timezone.utc) + timedelta(minutes=5)}
    token = jwt.encode(payload, settings_fixture.jwt_secret_key, algorithm="HS256")

    with pytest.raises(AuthException):
        authenticator_fixture.sub(token)


def test_sub_raises_auth_exception_for_non_uuid_sub_claim(
    authenticator_fixture: Authenticator, settings_fixture: Settings
):
    payload = {"sub": "not-a-uuid", "exp": datetime.now(timezone.utc) + timedelta(minutes=5)}
    token = jwt.encode(payload, settings_fixture.jwt_secret_key, algorithm="HS256")

    with pytest.raises(AuthException):
        authenticator_fixture.sub(token)


# JWT iat Tests
# ----------------------------------------------------------------------------------------------------------------------


def test_iat_raises_auth_exception_when_iat_claim_missing(
    authenticator_fixture: Authenticator, settings_fixture: Settings
):
    payload = {"sub": str(uuid.uuid4()), "exp": datetime.now(timezone.utc) + timedelta(minutes=5)}
    token = jwt.encode(payload, settings_fixture.jwt_secret_key, algorithm="HS256")

    with pytest.raises(AuthException):
        authenticator_fixture.iat(token)


def test_iat_raises_auth_exception_for_malformed_iat_claim(
    authenticator_fixture: Authenticator, settings_fixture: Settings
):
    payload = {
        "sub": str(uuid.uuid4()),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        "iat": "not-a-timestamp",
    }
    token = jwt.encode(payload, settings_fixture.jwt_secret_key, algorithm="HS256")
    with pytest.raises(AuthException):
        authenticator_fixture.iat(token)


def test_iat_returns_issued_at_datetime_from_token(
    authenticator_fixture: Authenticator, settings_fixture: Settings, user_fixture: User
):
    with time_machine.travel("2025-01-01 00:00:00"):
        issued_at = datetime.now(timezone.utc)
        expiration = issued_at + timedelta(minutes=5)
        payload = {"sub": str(user_fixture.id), "exp": expiration, "iat": int(issued_at.timestamp())}
        token = jwt.encode(payload, settings_fixture.jwt_secret_key, algorithm="HS256")

        iat = authenticator_fixture.iat(token)
        assert isinstance(iat, datetime)
        assert iat == issued_at


def test_iat_raises_auth_exception_for_malformed_jwt(authenticator_fixture: Authenticator):
    with pytest.raises(AuthException):
        authenticator_fixture.iat("invalid.token.value")


# JWT scopes Tests
# ----------------------------------------------------------------------------------------------------------------------


def test_scopes_returns_empty_set_when_scope_claim_missing(
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


def test_scopes_splits_space_delimited_scope_claim_into_set(
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


def test_scopes_returns_empty_set_for_empty_scope_claim(
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


def test_scopes_raises_auth_exception_for_malformed_token(authenticator_fixture: Authenticator):
    with pytest.raises(AuthException):
        authenticator_fixture.scopes("invalid.token.value")


# Tests for get_current_user
# ----------------------------------------------------------------------------------------------------------------------


def test_get_current_user_raises_authentication_failed_for_invalid_token(authenticator_fixture: Authenticator):
    with pytest.raises(AuthenticationFailedException):
        get_current_user("invalid.token.value", authenticator_fixture)


def test_get_current_user_returns_user_for_valid_access_token(authenticator_fixture: Authenticator, user_fixture: User):
    access_token, _ = authenticator_fixture.encode(user_fixture)
    user = get_current_user(access_token, authenticator_fixture)

    assert user.id == user_fixture.id
    assert user.username == user_fixture.username
    assert user.first_name == user_fixture.first_name
    assert user.last_name == user_fixture.last_name


def test_get_current_user_allows_access_when_token_scopes_include_requested_scopes(
    authenticator_fixture: Authenticator, user_fixture: User
):
    requested_scopes = {"user", "customer"}
    access_token, _ = authenticator_fixture.encode(user_fixture, requested_scopes=requested_scopes)
    user = get_current_user(access_token, authenticator_fixture, security_scopes=SecurityScopes(scopes=["user"]))

    assert user.id == user_fixture.id
    assert user.username == user_fixture.username
    assert user.first_name == user_fixture.first_name
    assert user.last_name == user_fixture.last_name


def test_get_current_user_raises_authorization_failed_when_scopes_do_not_match(
    authenticator_fixture: Authenticator, user_fixture: User
):
    requested_scopes = {"user"}
    access_token, _ = authenticator_fixture.encode(user_fixture, requested_scopes=requested_scopes)
    with pytest.raises(AuthorizationFailedException):
        get_current_user(access_token, authenticator_fixture, security_scopes=SecurityScopes(scopes=["admin"]))


def test_get_current_user_allows_access_when_no_scopes_requested(
    authenticator_fixture: Authenticator, user_fixture: User
):
    requested_scopes = {"user"}
    access_token, _ = authenticator_fixture.encode(user_fixture, requested_scopes=requested_scopes)
    user = get_current_user(access_token, authenticator_fixture)

    assert user.id == user_fixture.id
    assert user.username == user_fixture.username
    assert user.first_name == user_fixture.first_name
    assert user.last_name == user_fixture.last_name
