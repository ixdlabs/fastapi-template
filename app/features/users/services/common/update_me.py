import uuid
from fastapi import APIRouter, status
from pydantic import AwareDatetime, BaseModel, EmailStr, Field
from sqlalchemy import select

from app.core.audit_log import AuditLoggerDep
from app.core.auth import AuthenticationFailedException, CurrentUserDep
from app.core.background import BackgroundDep
from app.core.database import DbDep
from app.core.exceptions import ServiceException, raises
from app.features.users.models.user import User, UserType
from app.features.users.services.tasks.send_email_verification import SendEmailVerificationInput
from app.features.users.tasks import send_email_verification_task


router = APIRouter()


# Input/Output
# ----------------------------------------------------------------------------------------------------------------------


class UpdateMeInput(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=256)
    last_name: str = Field(..., min_length=1, max_length=256)
    email: EmailStr | None = Field(None, max_length=320)


class UpdateMeOutput(BaseModel):
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
    type = "users/common/update/user-not-found"
    detail = "User not found, the account may have already been deleted"


class EmailExistsException(ServiceException):
    status_code = status.HTTP_400_BAD_REQUEST
    type = "users/common/update/email-exists"
    detail = "Email is already in use by another account"


# Update user endpoint
# ----------------------------------------------------------------------------------------------------------------------


@raises(AuthenticationFailedException)
@raises(UserNotFoundException)
@raises(EmailExistsException)
@router.put("/me")
async def update_me(
    form: UpdateMeInput,
    db: DbDep,
    current_user: CurrentUserDep,
    background: BackgroundDep,
    audit_logger: AuditLoggerDep,
) -> UpdateMeOutput:
    """
    Update the current user's profile information.

    If the email is provided and is different from the current one, a verification email will be sent.
    The email update will only take effect after verification.
    """
    # Fetch user from database
    stmt = select(User).where(User.id == current_user.id)
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

        task_input = SendEmailVerificationInput(user_id=user.id, email=form.email)
        await background.submit(send_email_verification_task, task_input.model_dump_json())

    # Finalize update
    await audit_logger.record("update", user)
    await db.commit()
    await db.refresh(user)

    return UpdateMeOutput(
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
