import uuid
from fastapi import APIRouter, status
from pydantic import AwareDatetime, BaseModel, EmailStr
from sqlalchemy import select

from app.core.auth import AuthenticationFailedException, CurrentUserDep
from app.core.database import DbDep
from app.core.exceptions import ServiceException, raises
from app.features.users.models.user import User, UserType


router = APIRouter()


# Input/Output
# ----------------------------------------------------------------------------------------------------------------------


class DetailMeOutput(BaseModel):
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
    type = "users/common/detail-me/user-not-found"
    detail = "User not found, the account may have already been deleted"


# User detail endpoint
# ----------------------------------------------------------------------------------------------------------------------


@raises(AuthenticationFailedException)
@raises(UserNotFoundException)
@router.get("/me")
async def detail_me(db: DbDep, current_user: CurrentUserDep) -> DetailMeOutput:
    """Get detailed information about the currently authenticated user."""
    # Fetch user from database
    stmt = select(User).where(User.id == current_user.id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise UserNotFoundException()

    return DetailMeOutput(
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
