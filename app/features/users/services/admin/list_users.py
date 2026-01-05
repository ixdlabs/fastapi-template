from typing import Annotated, Literal
import uuid
from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.auth import AuthenticationFailedException, AuthorizationFailedException, CurrentAdminDep
from app.core.cache import CacheDep
from app.core.database import DbDep
from app.core.exceptions import raises
from app.core.pagination import Page, paginate
from app.core.rate_limit import RateLimitExceededException, rate_limit
from app.features.users.models.user import UserType, User


router = APIRouter()

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


# User list endpoint
# ----------------------------------------------------------------------------------------------------------------------


@raises(AuthenticationFailedException)
@raises(AuthorizationFailedException)
@raises(RateLimitExceededException)
@router.get("/")
@rate_limit("10/minute")
async def list_users(
    db: DbDep,
    query: Annotated[UserFilterInput, Query()],
    current_user: CurrentAdminDep,
    cache: CacheDep,
) -> Page[UserListOutput]:
    """
    List users in the system with optional search and pagination.
    The authenticated user must be an admin.

    This endpoint is rate-limited and cached for demonstration purposes.
    """
    # Check and return from cache
    response_cache = cache.vary_on_path().vary_on_query().vary_on_auth().with_ttl(60).build(Page[UserListOutput])
    if cache_result := await response_cache.get():
        return cache_result

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

    return await response_cache.set(response)
