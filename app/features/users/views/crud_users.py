from typing import Annotated, Literal
import uuid
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import AwareDatetime, BaseModel, EmailStr, Field
from sqlalchemy import select

from app.config.audit_log import AuditLoggerDep
from app.config.auth import CurrentUserDep
from app.config.background import BackgroundDep
from app.config.cache import CacheDep
from app.config.database import DbDep
from app.config.exceptions import raises
from app.config.pagination import Page, paginate
from app.config.rate_limit import RateLimitDep
from app.features.users.models import User, UserType
from app.features.users.tasks.email_verification import SendEmailVerificationInput, send_email_verification_email_task


class UserFilterInput(BaseModel):
    search: str | None = None
    limit: int = Field(100, gt=0, le=100)
    offset: int = Field(0, ge=0)
    order_by: Literal["created_at", "updated_at"] = "created_at"


class UserListOutput(BaseModel):
    id: uuid.UUID
    type: UserType
    username: str
    first_name: str
    last_name: str


class UserDetailOutput(BaseModel):
    id: uuid.UUID
    type: UserType
    username: str
    first_name: str
    last_name: str
    email: EmailStr | None
    joined_at: AwareDatetime
    created_at: AwareDatetime
    updated_at: AwareDatetime


class UserUpdateInput(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=256)
    last_name: str = Field(..., min_length=1, max_length=256)
    email: EmailStr | None = Field(None, max_length=320)


router = APIRouter()

# User detail endpoint
# ----------------------------------------------------------------------------------------------------------------------


@raises(status.HTTP_401_UNAUTHORIZED)
@raises(status.HTTP_403_FORBIDDEN)
@raises(status.HTTP_404_NOT_FOUND)
@router.get("/{user_id}")
async def detail_user(user_id: uuid.UUID, db: DbDep, current_user: CurrentUserDep, cache: CacheDep) -> UserDetailOutput:
    """
    Get detailed information about a specific user.
    The authenticated user must be an admin or the user themselves.

    This endpoint is cached for demonstration purposes.
    """
    # Check and return from cache
    cache.vary_on_path().vary_on_auth()
    if cache_result := await cache.get():
        return cache_result

    # Authorization check
    if current_user.type != UserType.ADMIN and current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this user")

    # Fetch user from database
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    response = UserDetailOutput(
        id=user.id,
        type=user.type,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        joined_at=user.joined_at,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )

    await cache.set(response, ttl=60)
    return response


# User list endpoint
# ----------------------------------------------------------------------------------------------------------------------


@raises(status.HTTP_401_UNAUTHORIZED)
@raises(status.HTTP_403_FORBIDDEN)
@raises(status.HTTP_429_TOO_MANY_REQUESTS)
@router.get("/")
async def list_users(
    db: DbDep,
    query: Annotated[UserFilterInput, Query()],
    current_user: CurrentUserDep,
    rate_limit: RateLimitDep,
    cache: CacheDep,
) -> Page[UserListOutput]:
    """
    List users in the system with optional search and pagination.
    The authenticated user must be an admin.

    This endpoint is rate-limited and cached for demonstration purposes.
    """
    # Rate limiting
    await rate_limit.limit("10/minute")

    # Check and return from cache
    cache.vary_on_path().vary_on_query().vary_on_auth()
    if cache_result := await cache.get():
        return cache_result

    # Authorization check
    if current_user.type != UserType.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to list users")

    # Build query with filters
    stmt = select(User)
    if query.search:
        search_pattern = f"%{query.search}%"
        stmt = stmt.where(
            User.username.ilike(search_pattern)
            | User.first_name.ilike(search_pattern)
            | User.last_name.ilike(search_pattern)
        )

    # Apply ordering, pagination, and execute
    order_column = User.created_at if query.order_by == "created_at" else User.updated_at
    stmt = stmt.order_by(order_column)
    result = await paginate(db, stmt, limit=query.limit, offset=query.offset)
    response = result.map_to(
        lambda user: UserListOutput(
            id=user.id,
            type=user.type,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
        )
    )

    return await cache.set(response, ttl=60)


# Delete user endpoint
# ----------------------------------------------------------------------------------------------------------------------


@raises(status.HTTP_401_UNAUTHORIZED)
@raises(status.HTTP_403_FORBIDDEN)
@raises(status.HTTP_404_NOT_FOUND)
@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: uuid.UUID, db: DbDep, current_user: CurrentUserDep, audit_logger: AuditLoggerDep
) -> None:
    """
    Delete a user from the system.
    The authenticated user must be an admin or the user themselves.
    """
    # Authorization check
    if current_user.type != UserType.ADMIN and current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this user")

    # Fetch user from database
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    await audit_logger.record("delete", user)
    await db.delete(user)
    await db.commit()


# Update user endpoint
# ----------------------------------------------------------------------------------------------------------------------


@raises(status.HTTP_401_UNAUTHORIZED)
@raises(status.HTTP_403_FORBIDDEN)
@raises(status.HTTP_404_NOT_FOUND)
@router.put("/{user_id}")
async def update_user(
    user_id: uuid.UUID,
    form: UserUpdateInput,
    db: DbDep,
    current_user: CurrentUserDep,
    background: BackgroundDep,
    audit_logger: AuditLoggerDep,
) -> UserDetailOutput:
    """
    Update a user's information.
    The authenticated user must be an admin or the user themselves.

    If the email is provided and is different from the current one, a verification email will be sent.
    The email update will only take effect after verification.
    """
    # Authorization check
    if current_user.type != UserType.ADMIN and current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this user")

    # Fetch user from database
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    await audit_logger.track(user)

    # Update user fields
    user.first_name = form.first_name
    user.last_name = form.last_name

    # If email is being updated, check for uniqueness and send verification email
    if form.email is not None and user.email != form.email:
        email_stmt = select(User).where(User.email == form.email).where(User.id != user.id)
        email_result = await db.execute(email_stmt)
        email_user = email_result.scalar_one_or_none()
        if email_user is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")

        task_input = SendEmailVerificationInput(user_id=user.id, email=form.email)
        await background.submit(send_email_verification_email_task, task_input.model_dump_json())

    # Finalize update
    await audit_logger.record("update", user)
    await db.commit()
    await db.refresh(user)

    return UserDetailOutput(
        id=user.id,
        type=user.type,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        joined_at=user.joined_at,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )
