import logging
import uuid
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.config.audit_log import AuditLoggerDep
from app.config.database import DbDep
from app.config.exceptions import raises
from app.features.users.models import UserAction, UserActionState, UserActionType

logger = logging.getLogger(__name__)


class ResetPasswordConfirmInput(BaseModel):
    action_id: uuid.UUID = Field(...)
    token: str = Field(...)
    new_password: str = Field(..., min_length=1, max_length=128)


class ResetPasswordConfirmOutput(BaseModel):
    detail: str = "Password has been reset successfully."


router = APIRouter()

# Password Reset Confirm endpoint
# ----------------------------------------------------------------------------------------------------------------------


@raises(status.HTTP_400_BAD_REQUEST)
@raises(status.HTTP_404_NOT_FOUND)
@router.post("/reset-password-confirm")
async def reset_password_confirm(
    form: ResetPasswordConfirmInput, db: DbDep, audit_logger: AuditLoggerDep
) -> ResetPasswordConfirmOutput:
    """Complete the password reset process using the action ID and token."""
    stmt = (
        select(UserAction)
        .join(UserAction.user)
        .options(joinedload(UserAction.user))
        .where(UserAction.id == form.action_id)
    )
    result = await db.execute(stmt)
    action = result.scalar_one_or_none()
    if action is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action not found")
    if action.type != UserActionType.PASSWORD_RESET:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid action type")
    if not action.is_valid(form.token):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid action token")

    action.user.set_password(form.new_password)
    action.state = UserActionState.COMPLETED

    await audit_logger.record("password_reset", action.user)
    await db.commit()

    return ResetPasswordConfirmOutput()
