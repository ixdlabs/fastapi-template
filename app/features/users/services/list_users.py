from typing import Annotated, Literal
import uuid
from fastapi import APIRouter, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.config.auth import AuthenticationFailedException, CurrentUserDep
from app.config.cache import CacheDep
from app.config.database import DbDep
from app.config.exceptions import ServiceException, raises
from app.config.pagination import Page, paginate
from app.config.rate_limit import RateLimitDep, RateLimitExceededException
from app.features.users.models import User, UserType


# Input/Output
# ----------------------------------------------------------------------------------------------------------------------


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


# Exceptions
# ----------------------------------------------------------------------------------------------------------------------


class UserListAccessNotAuthorizedException(ServiceException):
    status_code = status.HTTP_403_FORBIDDEN
    type = "users/list-users/not-authorized"
    detail = "Not authorized to list users"


# User list endpoint
# ----------------------------------------------------------------------------------------------------------------------


router = APIRouter()


@raises(AuthenticationFailedException)
@raises(UserListAccessNotAuthorizedException)
@raises(RateLimitExceededException)
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
        raise UserListAccessNotAuthorizedException()

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
