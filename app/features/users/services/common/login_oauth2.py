from typing import Annotated
from fastapi import APIRouter, status, Form
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.config.auth import AuthenticatorDep
from app.config.database import DbDep
from app.config.exceptions import ServiceException
from app.features.users.models.user import User


router = APIRouter()


# Input/Output
# ----------------------------------------------------------------------------------------------------------------------


class LoginInput(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=1, max_length=128)
    scope: str | None = Field(None, min_length=1, max_length=256)


class OAuth2TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# Exceptions
# ----------------------------------------------------------------------------------------------------------------------


class InvalidUsernameOrPasswordException(ServiceException):
    status_code = status.HTTP_401_UNAUTHORIZED
    type = "users/common/login-oauth2/invalid-credentials"
    detail = "Invalid username or password, please check your credentials and try again"


# Token endpoint (for OAuth2 compatibility)
# This in only implemented to support authentication in Swagger UI itself.
# ----------------------------------------------------------------------------------------------------------------------


@router.post("/oauth2/token", include_in_schema=False)
async def login_oauth2(
    form: Annotated[LoginInput, Form()], db: DbDep, authenticator: AuthenticatorDep
) -> OAuth2TokenResponse:
    stmt = select(User).where(User.username == form.username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise InvalidUsernameOrPasswordException()

    # Verify password
    password_valid = user.check_password(form.password)
    if not password_valid:
        raise InvalidUsernameOrPasswordException()

    # Generate tokens
    requested_scopes = set(form.scope.split()) if form.scope else None
    access_token, _ = authenticator.encode(user, requested_scopes)
    return OAuth2TokenResponse(access_token=access_token)
