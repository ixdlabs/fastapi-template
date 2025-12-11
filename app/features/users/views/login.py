from datetime import datetime, timedelta, timezone
from typing import Annotated
import uuid
from argon2 import PasswordHasher
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import select
import jwt

from app.config.database import DbDep
from app.config.settings import SettingsDep
from app.features.users.models import User


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
    input: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbDep, settings: SettingsDep
) -> OAuth2TokenResponse:
    input = LoginInput(username=input.username, password=input.password)
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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid username or password")

    try:
        password_hasher = PasswordHasher()
        password_hasher.verify(user.hashed_password, input.password)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid username or password")

    jwt_expiration = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expiration_minutes)
    jwt_payload = {"sub": str(user.id), "exp": jwt_expiration}
    access_token = jwt.encode(payload=jwt_payload, key=settings.jwt_secret_key, algorithm="HS256")

    return LoginOutput(
        access_token=access_token,
        user=LoginOutputUser(
            id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
        ),
    )
