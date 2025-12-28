from datetime import datetime, timedelta, timezone
import logging
from typing import Annotated
import uuid
from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy import update

from app.core.auth import CurrentTaskRunnerDep
from app.core.background import BackgroundTask, TaskRegistry
from app.core.database import DbDep
from app.core.email_sender import Email, EmailSenderDep
from app.core.settings import SettingsDep
from app.features.users.models.user_action import UserAction, UserActionState, UserActionType


logger = logging.getLogger(__name__)
router = APIRouter()
registry = TaskRegistry()


# Input/Output
# ----------------------------------------------------------------------------------------------------------------------


class SendPasswordResetInput(BaseModel):
    user_id: uuid.UUID
    email: EmailStr


class SendPasswordResetOutput(BaseModel):
    detail: str = "Password reset email sent successfully."
    action_id: uuid.UUID
    message_id: str
    token: str


# Task/Endpoint implementation
# ----------------------------------------------------------------------------------------------------------------------


@router.post("/send-password-reset-email")
async def send_password_reset_email(
    task_input: SendPasswordResetInput,
    *,
    current_user: CurrentTaskRunnerDep,
    settings: SettingsDep,
    db: DbDep,
    email_sender: EmailSenderDep,
) -> SendPasswordResetOutput:
    """
    Sends a password reset email to the user by creating a new password reset action.
    This invalidates any existing pending password reset actions for the user.
    """
    logger.info("Task running in worker=%s", current_user.worker_id)

    # Invalidate existing pending password reset actions
    update_stmt = (
        update(UserAction)
        .where(UserAction.user_id == task_input.user_id)
        .where(UserAction.state == UserActionState.PENDING)
        .where(UserAction.type == UserActionType.PASSWORD_RESET)
        .values(state=UserActionState.OBSOLETE)
    )
    _ = await db.execute(update_stmt)

    # Create a new password reset action
    token = str(uuid.uuid4())
    expiration = datetime.now(timezone.utc) + timedelta(minutes=settings.password_reset_expiration_minutes)
    action = UserAction(type=UserActionType.PASSWORD_RESET, user_id=task_input.user_id, expires_at=expiration)
    action.set_token(token)
    db.add(action)

    await db.commit()
    await db.refresh(action)

    message_id = await email_sender.send_email(
        Email(
            sender=settings.email_sender_address,
            receivers=[task_input.email],
            subject="Verify your email address",
            body_html_template=EMAIL_VERIFICATION_HTML_TEMPLATE,
            body_text_template=EMAIL_VERIFICATION_TEXT_TEMPLATE,
            template_data={"token": token},
        )
    )

    logger.info("Sending password reset email, action_id=%s, message_id=%s, token=%s", action.id, message_id, token)
    return SendPasswordResetOutput(action_id=action.id, message_id=message_id, token=token)


send_password_reset_email_task = registry.register_background_task(send_password_reset_email)
SendPasswordResetTaskDep = Annotated[BackgroundTask, Depends(send_password_reset_email_task)]


# Templates
# ----------------------------------------------------------------------------------------------------------------------

EMAIL_VERIFICATION_HTML_TEMPLATE = """
<html>
    <body>
        <p>Please verify your email address by clicking the link below:</p>
        <a href="https://example.com/verify-email?token={{ token }}">Verify Email</a>
    </body>
</html>
"""
EMAIL_VERIFICATION_TEXT_TEMPLATE = """
Please verify your email address by visiting the following link:https://example.com/verify-email?token={{ token }}
"""
