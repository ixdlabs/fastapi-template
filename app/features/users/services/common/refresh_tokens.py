import uuid
from fastapi import APIRouter, status
from pydantic import BaseModel, Field
from sqlalchemy import select
import logging

from app.config.auth import AuthenticatorDep, AuthException
from app.config.database import DbDep
from app.config.exceptions import ServiceException, raises
from app.features.users.models.user import User, UserType

logger = logging.getLogger(__name__)


router = APIRouter()


# Input/Output
# ----------------------------------------------------------------------------------------------------------------------


class RefreshInput(BaseModel):
    refresh_token: str = Field(..., min_length=1)


class RefreshOutput(BaseModel):
    access_token: str
    refresh_token: str
    user: "RefreshOutputUser"


class RefreshOutputUser(BaseModel):
    id: uuid.UUID
    type: UserType
    username: str
    first_name: str
    last_name: str


# Exceptions
# ----------------------------------------------------------------------------------------------------------------------


class InvalidRefreshTokenException(ServiceException):
    status_code = status.HTTP_401_UNAUTHORIZED
    type = "users/common/refresh-tokens/invalid-refresh-token"
    detail = "Invalid refresh token, please provide a valid token"


# Refresh endpoint
# ----------------------------------------------------------------------------------------------------------------------


@raises(InvalidRefreshTokenException)
@router.post("/refresh")
async def refresh_tokens(form: RefreshInput, db: DbDep, authenticator: AuthenticatorDep) -> RefreshOutput:
    """
    Refresh the user's tokens using refresh token and return new access and refresh tokens.

    If the user has changed their password since the refresh token was issued, the refresh token is invalidated.
    """
    # Validate refresh token
    try:
        user_id = authenticator.sub(form.refresh_token)
    except AuthException as e:
        logger.warning("token validation failed", exc_info=True)
        raise InvalidRefreshTokenException() from e

    # Check if the refresh token has expired
    try:
        iat = authenticator.iat(form.refresh_token)
    except AuthException as e:
        logger.warning("token iat extraction failed", exc_info=True)
        raise InvalidRefreshTokenException() from e

    # Fetch user by ID
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise InvalidRefreshTokenException()

    if user.password_set_at > iat:
        raise InvalidRefreshTokenException()

    # Generate new tokens
    access_token, refresh_token = authenticator.encode(user)
    return RefreshOutput(
        access_token=access_token,
        refresh_token=refresh_token,
        user=RefreshOutputUser(
            id=user.id,
            type=user.type,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
        ),
    )
