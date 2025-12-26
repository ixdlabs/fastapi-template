from datetime import datetime, timedelta, timezone
import logging
import uuid
from fastapi import APIRouter
from pydantic import BaseModel, EmailStr
from sqlalchemy import update

from app.config.auth import TaskRunnerDep
from app.config.database import DbDep
from app.config.settings import SettingsDep
from app.features.users.models.user_action import UserAction, UserActionState, UserActionType


logger = logging.getLogger(__name__)
router = APIRouter()


# Input/Output
# ----------------------------------------------------------------------------------------------------------------------


class SendPasswordResetInput(BaseModel):
    user_id: uuid.UUID
    email: EmailStr


class SendPasswordResetOutput(BaseModel):
    detail: str = "Password reset email sent successfully."
    action_id: uuid.UUID
    token: str


# Task/Endpoint implementation
# ----------------------------------------------------------------------------------------------------------------------


@router.post("/send-password-reset-email")
async def send_password_reset_email(
    task_input: SendPasswordResetInput, task_runner: TaskRunnerDep, settings: SettingsDep, db: DbDep
) -> SendPasswordResetOutput:
    """
    Sends a password reset email to the user by creating a new password reset action.
    This invalidates any existing pending password reset actions for the user.

    In the REST API, this endpoint is only reachable in debug mode to allow testing.
    """
    logger.info("Task initiated by runner_id=%s", task_runner.id)

    # Invalidate existing pending password reset actions
    update_stmt = (
        update(UserAction)
        .where(UserAction.user_id == task_input.user_id)
        .where(UserAction.state == UserActionState.PENDING)
        .where(UserAction.type == UserActionType.PASSWORD_RESET)
        .values(state=UserActionState.OBSOLETE)
    )
    await db.execute(update_stmt)

    # Create a new password reset action
    token = str(uuid.uuid4())
    expiration = datetime.now(timezone.utc) + timedelta(minutes=settings.password_reset_expiration_minutes)
    action = UserAction(type=UserActionType.PASSWORD_RESET, user_id=task_input.user_id, expires_at=expiration)
    action.set_token(token)
    db.add(action)

    await db.commit()
    await db.refresh(action)

    logger.info("Sending password reset email, action_id=%s, token=%s", action.id, token)
    return SendPasswordResetOutput(action_id=action.id, token=token)
