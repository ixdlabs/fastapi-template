import uuid
from fastapi import APIRouter, status
from pydantic import AwareDatetime, BaseModel, EmailStr, Field
from sqlalchemy import select

from app.config.audit_log import AuditLoggerDep
from app.config.auth import AuthenticationFailedException, CurrentUserDep
from app.config.database import DbDep
from app.config.exceptions import ServiceException, raises
from app.features.users.models.user import UserType, User


router = APIRouter()


# Input/Output
# ----------------------------------------------------------------------------------------------------------------------


class UserUpdateInput(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=256)
    last_name: str = Field(..., min_length=1, max_length=256)
    email: EmailStr | None = Field(None, max_length=320)


class UserUpdateOutput(BaseModel):
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


class UserUpdateNotAuthorizedException(ServiceException):
    status_code = status.HTTP_403_FORBIDDEN
    type = "users/admin/update/not-authorized"
    detail = "Not authorized to update this user"


class UserNotFoundException(ServiceException):
    status_code = status.HTTP_404_NOT_FOUND
    type = "users/admin/update/user-not-found"
    detail = "User not found"


class EmailExistsException(ServiceException):
    status_code = status.HTTP_400_BAD_REQUEST
    type = "users/admin/update/email-exists"
    detail = "Email already exists"


# Update user endpoint
# ----------------------------------------------------------------------------------------------------------------------


@raises(AuthenticationFailedException)
@raises(UserUpdateNotAuthorizedException)
@raises(UserNotFoundException)
@raises(EmailExistsException)
@router.put("/{user_id}")
async def update_user(
    user_id: uuid.UUID, form: UserUpdateInput, db: DbDep, current_user: CurrentUserDep, audit_logger: AuditLoggerDep
) -> UserUpdateOutput:
    """
    Update a user's information.
    The authenticated user must be an admin.
    """
    # Authorization check
    if current_user.type != UserType.ADMIN:
        raise UserUpdateNotAuthorizedException()

    # Fetch user from database
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise UserNotFoundException()

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
            raise EmailExistsException()

    # Finalize update
    await audit_logger.record("update", user)
    await db.commit()
    await db.refresh(user)

    return UserUpdateOutput(
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
