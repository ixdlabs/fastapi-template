from datetime import datetime, timedelta, timezone
import uuid
from fastapi import APIRouter, HTTPException, status
import jwt
from pydantic import BaseModel
from sqlalchemy import select
from argon2 import PasswordHasher

from app.config.database import DbDep
from app.config.settings import SettingsDep
from app.features.users.models import User


class RegisterInput(BaseModel):
    username: str
    password: str
    first_name: str
    last_name: str


class RegisterOutput(BaseModel):
    access_token: str
    user: "RegisterOutputUser"


class RegisterOutputUser(BaseModel):
    id: uuid.UUID
    username: str
    first_name: str
    last_name: str


router = APIRouter()

# Register endpoint
# ----------------------------------------------------------------------------------------------------------------------


@router.post("/register")
async def register(input: RegisterInput, db: DbDep, settings: SettingsDep) -> RegisterOutput:
    stmt = select(User).where(User.username == input.username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")

    password_hasher = PasswordHasher()
    user = User(
        id=uuid.uuid4(),
        username=input.username,
        first_name=input.first_name,
        last_name=input.last_name,
        hashed_password=password_hasher.hash(input.password),
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    jwt_expiration = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expiration_minutes)
    jwt_payload = {"sub": str(user.id), "exp": jwt_expiration}
    access_token = jwt.encode(payload=jwt_payload, key=settings.jwt_secret_key, algorithm="HS256")

    return RegisterOutput(
        access_token=access_token,
        user=RegisterOutputUser(
            id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
        ),
    )
