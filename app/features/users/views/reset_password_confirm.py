import logging
import uuid
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.config.audit_log import AuditLoggerDep
from app.config.database import DbDep
from app.config.exceptions import raises
from app.features.users.models import User, UserAction, UserActionState, UserActionType

logger = logging.getLogger(__name__)


class ResetPasswordConfirmInput(BaseModel):
    action_id: uuid.UUID = Field(...)
    token: str = Field(...)
    new_password: str = Field(..., min_length=1, max_length=128)


router = APIRouter()

# Password Reset Confirm endpoint
# ----------------------------------------------------------------------------------------------------------------------


@raises(status.HTTP_400_BAD_REQUEST)
@raises(status.HTTP_404_NOT_FOUND)
@router.post("/reset-password-confirm")
async def reset_password_confirm(form: ResetPasswordConfirmInput, db: DbDep, audit_logger: AuditLoggerDep):
    """Complete the password reset process using the action ID and token."""
    stmt = select(UserAction).where(UserAction.id == form.action_id)
    result = await db.execute(stmt)
    action = result.scalar_one_or_none()
    if action is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action not found")
    if action.type != UserActionType.PASSWORD_RESET:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid action type")
    if not action.is_valid(form.token):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid action token")

    user_stmt = select(User).where(User.id == action.user_id)
    user_result = await db.execute(user_stmt)
    user = user_result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.set_password(form.new_password)
    action.state = UserActionState.COMPLETED

    await audit_logger.record("password_reset", user)
    await db.commit()
