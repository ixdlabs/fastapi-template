from datetime import timedelta
import logging
from pathlib import Path
from typing import Annotated
from urllib.parse import urlencode
import uuid
from fastapi import Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy import update

from app.core.background import BackgroundTask, TaskRegistry
from app.core.database import DbWorkerDep
from app.core.email_sender import Email, EmailSenderWorkerDep
from app.core.settings import SettingsWorkerDep
from app.core.timezone import utc_now
from app.features.users.models.user_action import UserAction, UserActionState, UserActionType


logger = logging.getLogger(__name__)
email_templates_dir = Path(__file__).parent / "emails"

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


@registry.background_task("send_password_reset_email")
async def send_password_reset_email(
    task_input: SendPasswordResetInput, settings: SettingsWorkerDep, db: DbWorkerDep, email_sender: EmailSenderWorkerDep
) -> SendPasswordResetOutput:
    """
    Sends a password reset email to the user by creating a new password reset action.
    This invalidates any existing pending password reset actions for the user.
    """
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
    expiration = utc_now() + timedelta(minutes=settings.password_reset_expiration_minutes)
    action = UserAction(type=UserActionType.PASSWORD_RESET, user_id=task_input.user_id, expires_at=expiration)
    action.set_token(token)
    db.add(action)

    await db.commit()
    await db.refresh(action)

    password_reset_link_params = urlencode({"token": token, "action_id": action.id})
    password_reset_link = f"{settings.frontend_base_url}/reset-password?{password_reset_link_params}"
    message_id = await email_sender.send_email(
        Email(
            sender=settings.email_sender_address,
            receivers=[task_input.email],
            subject="Reset your password",
            body_html_template=email_templates_dir / "send_password_reset_email.mjml",
            body_text_template=email_templates_dir / "send_password_reset_email.txt",
            template_data={"password_reset_link": password_reset_link},
        )
    )

    logger.info("Sending password reset email, action_id=%s, message_id=%s, token=%s", action.id, message_id, token)
    return SendPasswordResetOutput(action_id=action.id, message_id=message_id, token=token)


SendPasswordResetTaskDep = Annotated[BackgroundTask, Depends(send_password_reset_email)]
