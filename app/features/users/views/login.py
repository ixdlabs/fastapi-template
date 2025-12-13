from typing import Annotated
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import select

from app.config.database import DbDep
from app.config.settings import SettingsDep
from app.features.users.models import User
from app.features.users.helpers import jwt_encode


class LoginInput(BaseModel):
    username: str
    password: str


class LoginOutput(BaseModel):
    access_token: str
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
# ----------------------------------------------------------------------------------------------------------------------


@router.post("/oauth2/token")
async def login_form(
    form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbDep, settings: SettingsDep
) -> OAuth2TokenResponse:
    input = LoginInput(username=form.username, password=form.password)
    result = await login(input, db, settings)
    return OAuth2TokenResponse(access_token=result.access_token, token_type="bearer")


# Login endpoint
# ----------------------------------------------------------------------------------------------------------------------


@router.post("/login")
async def login(input: LoginInput, db: DbDep, settings: SettingsDep) -> LoginOutput:
    stmt = select(User).where(User.username == input.username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    password_valid = user.check_password(input.password)
    if not password_valid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    access_token = jwt_encode(user, settings)
    return LoginOutput(
        access_token=access_token,
        user=LoginOutputUser(
            id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
        ),
    )
