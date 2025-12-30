from datetime import datetime, timedelta, timezone
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
from app.features.users.models.user_action import UserAction, UserActionState, UserActionType


logger = logging.getLogger(__name__)
email_templates_dir = Path(__file__).parent / "emails"

registry = TaskRegistry()


# Input/Output
# ----------------------------------------------------------------------------------------------------------------------


class SendEmailVerificationInput(BaseModel):
    user_id: uuid.UUID
    email: EmailStr


class SendEmailVerificationOutput(BaseModel):
    detail: str = "Email verification sent successfully."
    action_id: uuid.UUID
    message_id: str
    token: str


# Task/Endpoint implementation
# ----------------------------------------------------------------------------------------------------------------------


@registry.background_task("send_email_verification")
async def send_email_verification(
    task_input: SendEmailVerificationInput,
    settings: SettingsWorkerDep,
    db: DbWorkerDep,
    email_sender: EmailSenderWorkerDep,
) -> SendEmailVerificationOutput:
    """
    Sends an email verification email to the user by creating a new email verification action.
    This invalidates any existing pending email verification actions for the user.
    """
    # Invalidate existing pending email verification actions
    update_stmt = (
        update(UserAction)
        .where(UserAction.user_id == task_input.user_id)
        .where(UserAction.state == UserActionState.PENDING)
        .where(UserAction.type == UserActionType.EMAIL_VERIFICATION)
        .values(state=UserActionState.OBSOLETE)
    )
    _ = await db.execute(update_stmt)

    # Create a new email verification action
    token = str(uuid.uuid4())
    expiration = datetime.now(timezone.utc) + timedelta(minutes=settings.email_verification_expiration_minutes)
    action = UserAction(
        type=UserActionType.EMAIL_VERIFICATION,
        user_id=task_input.user_id,
        data={"email": task_input.email},
        expires_at=expiration,
    )
    action.set_token(token)
    db.add(action)

    await db.commit()
    await db.refresh(action)

    verification_link_params = urlencode({"token": token, "email": task_input.email})
    verification_link = f"{settings.frontend_base_url}/verify-email?{verification_link_params}"
    message_id = await email_sender.send_email(
        Email(
            sender=settings.email_sender_address,
            receivers=[task_input.email],
            subject="Verify your email address",
            body_html_template=email_templates_dir / "send_email_verification.mjml",
            body_text_template=email_templates_dir / "send_email_verification.txt",
            template_data={"verification_link": verification_link},
        )
    )

    logger.info("Sent email verification, action_id=%s,  message_id=%s, token=%s", action.id, message_id, token)
    return SendEmailVerificationOutput(action_id=action.id, token=token, message_id=message_id)


SendEmailVerificationTaskDep = Annotated[BackgroundTask, Depends(send_email_verification)]
