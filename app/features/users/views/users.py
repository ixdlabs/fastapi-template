from datetime import datetime
from typing import Annotated, Literal
import uuid
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.config.auth import CurrentUserDep
from app.config.cache import CacheDep
from app.config.database import DbDep
from app.config.pagination import Page, paginate
from app.config.rate_limit import RateLimitDep
from app.features.users.models import User


class UserFilterInput(BaseModel):
    search: str | None = None
    limit: int = Field(100, gt=0, le=100)
    offset: int = Field(0, ge=0)
    order_by: Literal["created_at", "updated_at"] = "created_at"


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
    first_name: str = Field(..., min_length=1, max_length=256)
    last_name: str = Field(..., min_length=1, max_length=256)


router = APIRouter()

# User detail endpoint
# ----------------------------------------------------------------------------------------------------------------------


@router.get("/{user_id}")
async def user_detail(user_id: uuid.UUID, db: DbDep, current_user: CurrentUserDep, cache: CacheDep) -> UserDetailOutput:
    """Get detailed information about a specific user."""
    cache.vary_on_path().vary_on_auth()
    if cache_result := await cache.get():
        return cache_result

    if current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this user")

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    assert user is not None, "User not found - Sanity check failed"

    response = UserDetailOutput(
        id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )

    await cache.set(response, ttl=60)
    return response


# User list endpoint
# This endpoint is cached and rate-limited for demonstration purposes
# ----------------------------------------------------------------------------------------------------------------------


@router.get("/")
async def user_list(
    db: DbDep, query: Annotated[UserFilterInput, Query()], rate_limit: RateLimitDep, cache: CacheDep
) -> Page[UserListOutput]:
    """List users with optional filtering, caching, and rate limiting."""
    cache.vary_on_path().vary_on_query()
    if cache_result := await cache.get():
        return cache_result

    await rate_limit.limit("10/minute")

    stmt = select(User)
    if query.search:
        search_pattern = f"%{query.search}%"
        stmt = stmt.where(
            User.username.ilike(search_pattern)
            | User.first_name.ilike(search_pattern)
            | User.last_name.ilike(search_pattern)
        )

    order_column = User.created_at if query.order_by == "created_at" else User.updated_at
    stmt = stmt.order_by(order_column)
    result = await paginate(db, stmt, limit=query.limit, offset=query.offset)
    response = result.map_to(
        lambda user: UserListOutput(
            id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
        )
    )

    return await cache.set(response, ttl=60)


# Delete user endpoint
# ----------------------------------------------------------------------------------------------------------------------


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: uuid.UUID, db: DbDep, current_user: CurrentUserDep) -> None:
    """Delete a user by ID."""
    if current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this user")

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    assert user is not None, "User not found - Sanity check failed"

    await db.delete(user)
    await db.commit()


# Update user endpoint
# ----------------------------------------------------------------------------------------------------------------------


@router.put("/{user_id}")
async def update_user(
    user_id: uuid.UUID, form: UserUpdateInput, db: DbDep, current_user: CurrentUserDep
) -> UserDetailOutput:
    """Update a user's first and last name."""
    if current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this user")

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    assert user is not None, "User not found - Sanity check failed"

    user.first_name = form.first_name
    user.last_name = form.last_name
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
