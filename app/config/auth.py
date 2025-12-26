"""
This module contains authentication dependencies for FastAPI routes.
It provides a way to retrieve the current authenticated user based on a JWT token.

Docs: https://fastapi.tiangolo.com/tutorial/security/
"""

from datetime import datetime, timedelta, timezone
import logging
from typing import Annotated, Any
import uuid

from fastapi import Depends, Security, status
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
import jwt
from pydantic import BaseModel, ValidationError

from app.config.exceptions import ServiceException
from app.config.settings import Settings, SettingsDep
from app.features.users.models.user import User, UserType

logger = logging.getLogger(__name__)

# Model representing the authenticated user data in JWT tokens
# ----------------------------------------------------------------------------------------------------------------------


class AuthUser(BaseModel):
    id: uuid.UUID
    type: UserType | None = None
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None


class AuthException(BaseException):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__()


class Authenticator:
    def __init__(self, settings: Settings):
        self.settings = settings

    def encode(self, user: User, requested_scopes: set[str] | None = None) -> tuple[str, str]:
        """Encode a JWT access token + refresh token for the given user."""
        current_time = datetime.now(timezone.utc)
        access_exp = current_time + timedelta(minutes=self.settings.jwt_access_expiration_minutes)
        refresh_exp = current_time + timedelta(minutes=self.settings.jwt_refresh_expiration_minutes)

        # Determine user scopes
        user_scopes = user.get_oauth2_scopes()
        # In debug mode, admin users get the "task" scope
        # This allows admins to execute background tasks via REST API
        if self.settings.debug and user.type == UserType.ADMIN:
            user_scopes.add("task")
        if requested_scopes is not None:
            if not requested_scopes.issubset(user_scopes):
                raise AuthException("Requested scopes are not a subset of user scopes")
            user_scopes = requested_scopes

        scope = " ".join(sorted(user_scopes))

        # User object to be included in the token
        auth_user = AuthUser(
            id=user.id,
            type=user.type,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
        )

        # Create JWT tokens
        user_id = str(user.id)
        user_dump = auth_user.model_dump_json()
        access_payload = {"type": "access", "sub": user_id, "exp": access_exp, "user": user_dump, "scope": scope}
        refresh_payload = {"type": "refresh", "sub": user_id, "iat": current_time, "exp": refresh_exp, "scope": scope}

        access_token = jwt.encode(algorithm="HS256", key=self.settings.jwt_secret_key, payload=access_payload)
        refresh_token = jwt.encode(algorithm="HS256", key=self.settings.jwt_secret_key, payload=refresh_payload)
        return access_token, refresh_token

    def user(self, access_token: str) -> AuthUser:
        """Extract the user information from the given JWT access token."""
        try:
            payload: dict[str, Any] = jwt.decode(access_token, self.settings.jwt_secret_key, algorithms=["HS256"])
        except jwt.PyJWTError as e:
            raise AuthException("JWT decode error") from e

        if payload.get("type") != "access":
            raise AuthException("Invalid JWT access token (wrong type)")

        user_data = payload.get("user")
        if user_data is None:
            raise AuthException("Invalid JWT access token (missing user data)")

        try:
            user = AuthUser.model_validate_json(user_data)
        except ValidationError as e:
            raise AuthException("AuthUser validation error") from e

        return user

    def scopes(self, token: str) -> set[str]:
        """Extract the scopes from the given JWT token."""
        try:
            payload: dict[str, Any] = jwt.decode(token, self.settings.jwt_secret_key, algorithms=["HS256"])
        except jwt.PyJWTError as e:
            raise AuthException("JWT decode error") from e

        scope_str = str(payload.get("scope", ""))
        return set(scope_str.split()) if scope_str else set()

    def sub(self, token: str) -> uuid.UUID:
        """Extract the subject (user ID) from the given JWT token."""
        try:
            payload: dict[str, Any] = jwt.decode(token, self.settings.jwt_secret_key, algorithms=["HS256"])
        except jwt.PyJWTError as e:
            raise AuthException("JWT decode error") from e

        user_id = payload.get("sub")
        if user_id is None:
            raise AuthException("Invalid JWT access token (missing user ID)")

        try:
            user_id = uuid.UUID(user_id)
        except ValueError as e:
            raise AuthException("Invalid JWT access token (Invalid UUID format for user ID)") from e

        return user_id

    def iat(self, token: str) -> datetime:
        """Extract the issued-at time from the given JWT token."""
        try:
            payload: dict[str, Any] = jwt.decode(token, self.settings.jwt_secret_key, algorithms=["HS256"])
        except jwt.PyJWTError as e:
            raise AuthException("JWT decode error") from e

        iat_timestamp = payload.get("iat")
        if iat_timestamp is None or not isinstance(iat_timestamp, (int, float)):
            raise AuthException("Invalid JWT token (missing issued-at time)")

        return datetime.fromtimestamp(iat_timestamp, tz=timezone.utc)


def get_authenticator(settings: SettingsDep) -> Authenticator:
    return Authenticator(settings)


AuthenticatorDep = Annotated[Authenticator, Depends(get_authenticator)]


# Exceptions
# ----------------------------------------------------------------------------------------------------------------------


class AuthenticationFailedException(ServiceException):
    status_code = status.HTTP_401_UNAUTHORIZED
    type = "auth/authentication-failed"
    detail = "Authentication failed, please login again"

    def __init__(self, authenticate_value: str | None = None) -> None:
        headers: dict[str, str] | None = None
        if authenticate_value:
            headers = {"WWW-Authenticate": authenticate_value}
        super().__init__(headers=headers)


class AuthorizationFailedException(ServiceException):
    status_code = status.HTTP_403_FORBIDDEN
    type = "auth/authorization-failed"
    detail = "You do not have permission to access this resource"

    def __init__(self, authenticate_value: str | None = None) -> None:
        headers: dict[str, str] | None = None
        if authenticate_value:
            headers = {"WWW-Authenticate": authenticate_value}
        super().__init__(headers=headers)


class TaskRunningPermissionDeniedException(ServiceException):
    status_code = status.HTTP_401_UNAUTHORIZED
    type = "auth/task-running-permission-denied"
    detail = "Task running permission denied, this is only allowed in debug mode"


# Dependency to get the current authenticated user
# ----------------------------------------------------------------------------------------------------------------------

oauth2_scheme = OAuth2PasswordBearer(
    scheme_name="JWT",
    tokenUrl="/api/auth/oauth2/token",
    refreshUrl="/api/auth/refresh",
    scopes={
        "user": "Authenticated user access",
        "customer": "Customer access",
        "admin": "Administrator access",
        "task": "Task runner access",
    },
)


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    authenticator: AuthenticatorDep,
    security_scopes: SecurityScopes = SecurityScopes(scopes=[]),
) -> AuthUser:
    if security_scopes is None:
        security_scopes = SecurityScopes(scopes=[])

    if security_scopes.scopes:
        authenticate_value = f'Bearer scope="{security_scopes.scope_str}"'
    else:
        authenticate_value = "Bearer"

    try:
        user = authenticator.user(token)
        scopes = authenticator.scopes(token)
    except AuthException as e:
        logger.warning("token validation failed", exc_info=True)
        raise AuthenticationFailedException(authenticate_value) from e

    if not set(security_scopes.scopes).issubset(scopes):
        logger.warning("authorization failed: required scopes=%s, token scopes=%s", security_scopes.scopes, scopes)
        raise AuthorizationFailedException(authenticate_value)

    return user


CurrentUserDep = Annotated[AuthUser, Security(get_current_user, scopes=["user"])]
CurrentAdminDep = Annotated[AuthUser, Security(get_current_user, scopes=["admin"])]
CurrentCustomerDep = Annotated[AuthUser, Security(get_current_user, scopes=["customer"])]
CurrentTaskRunnerDep = Annotated[AuthUser, Security(get_current_user, scopes=["task"])]
