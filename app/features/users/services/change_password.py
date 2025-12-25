import logging
from fastapi import APIRouter, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.config.audit_log import AuditLoggerDep
from app.config.auth import AuthenticationFailedException, CurrentUserDep
from app.config.database import DbDep
from app.config.exceptions import ServiceException, raises
from app.features.users.models import User

logger = logging.getLogger(__name__)


# Input/Output
# ----------------------------------------------------------------------------------------------------------------------


class ChangePasswordInput(BaseModel):
    old_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=1, max_length=128)


class ChangePasswordOutput(BaseModel):
    detail: str = "Password change successful."


# Exceptions
# ----------------------------------------------------------------------------------------------------------------------


class UserNotFoundException(ServiceException):
    status_code = status.HTTP_404_NOT_FOUND
    type = "users/change-password/user-not-found"
    detail = "User not found"


class PasswordIncorrectException(ServiceException):
    status_code = status.HTTP_400_BAD_REQUEST
    type = "users/change-password/password-incorrect"
    detail = "Old password is incorrect"


class PasswordsIdenticalException(ServiceException):
    status_code = status.HTTP_400_BAD_REQUEST
    type = "users/change-password/passwords-identical"
    detail = "New password must be different from old password"


# Change Password endpoint
# ----------------------------------------------------------------------------------------------------------------------

router = APIRouter()


@raises(AuthenticationFailedException)
@raises(PasswordIncorrectException)
@raises(UserNotFoundException)
@raises(PasswordsIdenticalException)
@router.post("/change-password")
async def change_password(
    form: ChangePasswordInput, current_user: CurrentUserDep, db: DbDep, audit_logger: AuditLoggerDep
) -> ChangePasswordOutput:
    """
    Change the password for the current user using the old password for verification.
    The new password must be different from the old password.
    Previously issued refresh tokens will be invalidated (not implemented yet).
    """
    # Fetch the current user from the database
    stmt = select(User).where(User.id == current_user.id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise UserNotFoundException()

    # Verify old password and check new password validity
    if not user.check_password(form.old_password):
        raise PasswordIncorrectException()
    if form.old_password == form.new_password:
        raise PasswordsIdenticalException()

    # Update the user's password
    user.set_password(form.new_password)
    await audit_logger.record("change_password", user)
    await db.commit()

    return ChangePasswordOutput()
