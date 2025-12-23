from typing import Annotated
import uuid
from fastapi import APIRouter, HTTPException, status, Form
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.config.auth import AuthenticatorDep
from app.config.database import DbDep
from app.features.users.models import User


class LoginInput(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=1, max_length=128)


class LoginOutput(BaseModel):
    access_token: str
    refresh_token: str
    user: "LoginOutputUser"


class LoginOutputUser(BaseModel):
    id: uuid.UUID
    username: str
    first_name: str
    last_name: str


class OAuth2TokenResponse(BaseModel):
    access_token: str
    token_type: str


router = APIRouter()


# Token endpoint (for OAuth2 compatibility)
# This in only implemented to support authentication in Swagger UI itself.
# ----------------------------------------------------------------------------------------------------------------------


@router.post("/oauth2/token", include_in_schema=False)
async def oauth2(
    form: Annotated[LoginInput, Form()], db: DbDep, authenticator: AuthenticatorDep
) -> OAuth2TokenResponse:
    result = await login(form, db, authenticator)
    return OAuth2TokenResponse(access_token=result.access_token, token_type="bearer")


# Login endpoint
# ----------------------------------------------------------------------------------------------------------------------


@router.post("/login")
async def login(form: LoginInput, db: DbDep, authenticator: AuthenticatorDep) -> LoginOutput:
    """Login user."""
    stmt = select(User).where(User.username == form.username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    password_valid = user.check_password(form.password)
    if not password_valid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    access_token, refresh_token = authenticator.encode(user)
    return LoginOutput(
        access_token=access_token,
        refresh_token=refresh_token,
        user=LoginOutputUser(
            id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
        ),
    )
