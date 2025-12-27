import uuid
from fastapi import APIRouter, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.config.audit_log import AuditLoggerDep
from app.config.database import DbDep
from app.config.exceptions import ServiceException, raises
from app.features.users.models.user import User
from app.features.users.models.user_action import UserAction, UserActionState, UserActionType


router = APIRouter()


# Input/Output
# ----------------------------------------------------------------------------------------------------------------------


class VerifyEmailInput(BaseModel):
    action_id: uuid.UUID = Field(...)
    token: str = Field(..., min_length=1, max_length=128)


class VerifyEmailOutput(BaseModel):
    user_id: uuid.UUID
    email: str


# Exceptions
# ----------------------------------------------------------------------------------------------------------------------


class ActionNotFoundException(ServiceException):
    status_code = status.HTTP_404_NOT_FOUND
    type = "users/common/verify-email-confirm/action-not-found"
    detail = "Action not found,  it may have already been used or expired"


class InvalidActionTokenException(ServiceException):
    status_code = status.HTTP_400_BAD_REQUEST
    type = "users/common/verify-email-confirm/invalid-action-token"
    detail = "Invalid action token,  it may have already been used or expired"


class EmailAlreadyInUseException(ServiceException):
    status_code = status.HTTP_400_BAD_REQUEST
    type = "users/common/verify-email-confirm/email-already-in-use"
    detail = "Email is already in use by another user"


# Verify Email endpoint
# ----------------------------------------------------------------------------------------------------------------------


@raises(ActionNotFoundException)
@raises(InvalidActionTokenException)
@raises(EmailAlreadyInUseException)
@router.post("/verify-email")
async def verify_email_confirm(form: VerifyEmailInput, db: DbDep, audit_logger: AuditLoggerDep) -> VerifyEmailOutput:
    """
    Verify and set a user's email using a valid action token.
    The email must not be already in use by another user.
    """
    # Retrieve the action record
    stmt = (
        select(UserAction)
        .join(UserAction.user)
        .options(joinedload(UserAction.user))
        .where(UserAction.id == form.action_id)
    )
    result = await db.execute(stmt)
    action = result.scalar_one_or_none()
    if action is None:
        raise ActionNotFoundException()

    # Validate action
    if action.type != UserActionType.EMAIL_VERIFICATION:
        raise InvalidActionTokenException()
    if not action.is_valid(form.token):
        raise InvalidActionTokenException()
    if action.data is None or "email" not in action.data or not isinstance(action.data["email"], str):
        raise InvalidActionTokenException()
    action_email = action.data["email"]

    user = action.user
    user_id = user.id

    # Check if email is already used by another user
    email_other_stmt = select(User).where(User.email == action_email).where(User.id != user_id)
    email_other_result = await db.execute(email_other_stmt)
    email_other_user = email_other_result.scalar_one_or_none()
    if email_other_user is not None:
        raise EmailAlreadyInUseException()

    # Update user email and action state
    await audit_logger.track(user)
    user.email = action_email
    action.state = UserActionState.COMPLETED

    # Finalize
    await audit_logger.record("verify_email", user)
    await db.commit()

    return VerifyEmailOutput(user_id=user_id, email=action_email)
