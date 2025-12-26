import logging
import uuid
from fastapi import APIRouter, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.config.audit_log import AuditLoggerDep
from app.config.database import DbDep
from app.config.exceptions import ServiceException, raises
from app.features.users.models.user_action import UserAction, UserActionState, UserActionType

logger = logging.getLogger(__name__)
router = APIRouter()


# Input/Output
# ----------------------------------------------------------------------------------------------------------------------


class ResetPasswordConfirmInput(BaseModel):
    action_id: uuid.UUID = Field(...)
    token: str = Field(...)
    new_password: str = Field(..., min_length=1, max_length=128)


class ResetPasswordConfirmOutput(BaseModel):
    detail: str = "Password has been reset successfully."


# Exceptions
# ----------------------------------------------------------------------------------------------------------------------


class ActionNotFoundException(ServiceException):
    status_code = status.HTTP_404_NOT_FOUND
    type = "users/common/reset-password-confirm/action-not-found"
    detail = "Action not found, it may have already been used or expired"


class InvalidActionTokenException(ServiceException):
    status_code = status.HTTP_400_BAD_REQUEST
    type = "users/common/reset-password-confirm/invalid-action-token"
    detail = "Invalid action token, it may have already been used or expired"


# Password Reset Confirm endpoint
# ----------------------------------------------------------------------------------------------------------------------


@raises(ActionNotFoundException)
@raises(InvalidActionTokenException)
@router.post("/reset-password-confirm")
async def reset_password_confirm(
    form: ResetPasswordConfirmInput, db: DbDep, audit_logger: AuditLoggerDep
) -> ResetPasswordConfirmOutput:
    """
    Reset a user's password using a valid action token.
    Previously issued refresh tokens will be invalidated.
    """
    # Fetch action by ID
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
    if action.type != UserActionType.PASSWORD_RESET:
        raise InvalidActionTokenException()
    if not action.is_valid(form.token):
        raise InvalidActionTokenException()

    # Reset password
    action.user.set_password(form.new_password)
    action.state = UserActionState.COMPLETED

    # Finalize
    await audit_logger.record("reset_password", action.user)
    await db.commit()

    return ResetPasswordConfirmOutput()
