"""
This module contains authentication dependencies for FastAPI routes.
It provides a way to retrieve the current authenticated user based on a JWT token.

Docs: https://fastapi.tiangolo.com/tutorial/security/
"""

from datetime import datetime, timedelta, timezone
import logging
from typing import Annotated
import uuid

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from pydantic import BaseModel, ValidationError

from app.config.settings import Settings, SettingsDep
from app.features.users.models import User

logger = logging.getLogger(__name__)

# Model representing the authenticated user data in JWT tokens
# ----------------------------------------------------------------------------------------------------------------------


class AuthUser(BaseModel):
    id: uuid.UUID
    username: str
    first_name: str
    last_name: str


class AuthException(BaseException):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__()


class Authenticator:
    def __init__(self, settings: Settings):
        self.settings = settings

    def encode(self, user: User) -> tuple[str, str]:
        """Encode a JWT access token + refresh token for the given user."""
        current_time = datetime.now(timezone.utc)
        access_expiration = current_time + timedelta(minutes=self.settings.jwt_access_expiration_minutes)
        refresh_expiration = current_time + timedelta(minutes=self.settings.jwt_refresh_expiration_minutes)

        auth_user = AuthUser(id=user.id, username=user.username, first_name=user.first_name, last_name=user.last_name)
        access_payload = {"sub": str(user.id), "exp": access_expiration, "user": auth_user.model_dump_json()}
        refresh_payload = {"sub": str(user.id), "exp": refresh_expiration}

        access_token = jwt.encode(payload=access_payload, key=self.settings.jwt_secret_key, algorithm="HS256")
        refresh_token = jwt.encode(payload=refresh_payload, key=self.settings.jwt_secret_key, algorithm="HS256")
        return access_token, refresh_token

    def user(self, access_token: str) -> AuthUser:
        """Extract the user information from the given JWT access token."""
        try:
            payload = jwt.decode(access_token, self.settings.jwt_secret_key, algorithms=["HS256"])
        except jwt.PyJWTError as e:
            raise AuthException("JWT decode error") from e

        user_data = payload.get("user")
        if user_data is None:
            raise AuthException("Invalid JWT access token (missing user data)")

        try:
            user = AuthUser.model_validate_json(user_data)
        except ValidationError as e:
            raise AuthException("AuthUser validation error") from e

        return user

    def sub(self, token: str) -> uuid.UUID:
        """Extract the subject (user ID) from the given JWT token."""
        try:
            payload = jwt.decode(token, self.settings.jwt_secret_key, algorithms=["HS256"])
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


def get_authenticator(settings: SettingsDep) -> Authenticator:
    return Authenticator(settings)


AuthenticatorDep = Annotated[Authenticator, Depends(get_authenticator)]


# Dependency to get the current authenticated user
# ----------------------------------------------------------------------------------------------------------------------

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/oauth2/token", scheme_name="JWT")


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], authenticator: AuthenticatorDep) -> AuthUser:
    try:
        return authenticator.user(token)
    except AuthException as e:
        logger.warning("token validation failed", exc_info=True)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials") from e


CurrentUserDep = Annotated[AuthUser, Security(get_current_user)]
