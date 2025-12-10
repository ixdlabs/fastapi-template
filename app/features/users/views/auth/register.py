import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from argon2 import PasswordHasher

from app.config.database import DbDep
from app.features.users.models import User


class RegisterInput(BaseModel):
    username: str
    password: str
    first_name: str
    last_name: str


class RegisterOutput(BaseModel):
    access_token: str
    refresh_token: str
    user: "RegisterOutputUser"


class RegisterOutputUser(BaseModel):
    id: uuid.UUID
    username: str
    first_name: str
    last_name: str


router = APIRouter()


@router.post("/register")
async def register(input: RegisterInput, db: DbDep) -> RegisterOutput:
    stmt = select(User).where(User.username == input.username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is not None:
        raise HTTPException(status_code=400, detail="Username already exists")

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

    return RegisterOutput(
        access_token="dummy_access_token",
        refresh_token="dummy_refresh_token",
        user=RegisterOutputUser(
            id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
        ),
    )
