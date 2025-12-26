import uuid
from fastapi import APIRouter, status
from pydantic import AwareDatetime, BaseModel, EmailStr
from sqlalchemy import select

from app.config.auth import AuthenticationFailedException, AuthorizationFailedException, CurrentAdminDep
from app.config.cache import CacheDep
from app.config.database import DbDep
from app.config.exceptions import ServiceException, raises
from app.features.users.models.user import UserType, User


router = APIRouter()


# Input/Output
# ----------------------------------------------------------------------------------------------------------------------


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


# Exceptions
# ----------------------------------------------------------------------------------------------------------------------


class UserNotFoundException(ServiceException):
    status_code = status.HTTP_404_NOT_FOUND
    type = "users/admin/detail-user/user-not-found"
    detail = "User not found"


# User detail endpoint
# ----------------------------------------------------------------------------------------------------------------------


@raises(AuthenticationFailedException)
@raises(AuthorizationFailedException)
@raises(UserNotFoundException)
@router.get("/{user_id}")
async def detail_user(
    user_id: uuid.UUID, db: DbDep, current_user: CurrentAdminDep, cache: CacheDep
) -> UserDetailOutput:
    """
    Get detailed information about a specific user.
    The authenticated user must be an admin.

    This endpoint is cached for demonstration purposes.
    """
    assert current_user.type == UserType.ADMIN

    # Check and return from cache
    cache.vary_on_path().vary_on_auth()
    if cache_result := await cache.get():
        return cache_result

    # Fetch user from database
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise UserNotFoundException()

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
