from datetime import datetime
import uuid
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from app.config.auth import CurrentUserDep
from app.config.database import DbDep
from app.features.users.models import User


class UserListOutput(BaseModel):
    id: uuid.UUID
    username: str
    first_name: str
    last_name: str


class UserDetailOutput(BaseModel):
    id: uuid.UUID
    username: str
    first_name: str
    last_name: str
    created_at: datetime
    updated_at: datetime


class UserUpdateInput(BaseModel):
    first_name: str
    last_name: str


router = APIRouter()

# Me endpoint (Current user detail)
# ----------------------------------------------------------------------------------------------------------------------


@router.get("/me")
async def me(current_user: CurrentUserDep) -> UserDetailOutput:
    return UserDetailOutput(
        id=current_user.id,
        username=current_user.username,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
    )


# User detail endpoint
# ----------------------------------------------------------------------------------------------------------------------


@router.get("/{user_id}")
async def user_detail(user_id: uuid.UUID, db: DbDep, current_user: CurrentUserDep) -> UserDetailOutput:
    if current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this user")

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return UserDetailOutput(
        id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


# User list endpoint
# ----------------------------------------------------------------------------------------------------------------------


@router.get("/")
async def user_list(db: DbDep) -> list[UserListOutput]:
    stmt = select(User)
    result = await db.execute(stmt)
    users = result.scalars().all()

    return [
        UserListOutput(
            id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
        )
        for user in users
    ]


# Delete user endpoint
# ----------------------------------------------------------------------------------------------------------------------


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: uuid.UUID, db: DbDep, current_user: CurrentUserDep) -> None:
    if current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this user")

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    await db.delete(user)
    await db.commit()


# Update user endpoint
# ----------------------------------------------------------------------------------------------------------------------


@router.put("/{user_id}")
async def update_user(
    user_id: uuid.UUID, input: UserUpdateInput, db: DbDep, current_user: CurrentUserDep
) -> UserDetailOutput:
    if current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this user")

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.first_name = input.first_name
    user.last_name = input.last_name
    await db.commit()
    await db.refresh(user)

    return UserDetailOutput(
        id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )
