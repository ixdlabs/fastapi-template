import uuid
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from app.config.database import DbDep
from app.config.settings import SettingsDep
from app.features.users.models import User
from app.features.users.helpers import jwt_encode


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


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(input: RegisterInput, db: DbDep, settings: SettingsDep) -> RegisterOutput:
    stmt = select(User).where(User.username == input.username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")

    user = User(username=input.username, first_name=input.first_name, last_name=input.last_name)
    user.set_password(input.password)

    db.add(user)
    await db.commit()
    await db.refresh(user)

    access_token = jwt_encode(user, settings)
    return RegisterOutput(
        access_token=access_token,
        user=RegisterOutputUser(
            id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
        ),
    )
