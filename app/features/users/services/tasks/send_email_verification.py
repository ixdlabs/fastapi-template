from datetime import datetime, timedelta, timezone
import logging
from pathlib import Path
from typing import Annotated
from urllib.parse import urlencode
import uuid
from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy import update

from app.core.auth import CurrentTaskRunnerDep, CurrentWorkerDep
from app.core.background import BackgroundTask, TaskRegistry
from app.core.database import DbDep, DbWorkerDep
from app.core.email_sender import Email, EmailSenderDep, EmailSenderWorkerDep
from app.core.settings import SettingsDep, SettingsWorkerDep
from app.features.users.models.user_action import UserAction, UserActionState, UserActionType


logger = logging.getLogger(__name__)
email_templates_dir = Path(__file__).parent / "emails"
router = APIRouter()
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


@router.post("/send-email-verification")
async def send_email_verification(
    task_input: SendEmailVerificationInput,
    db: DbDep,
    settings: SettingsDep,
    current_user: CurrentTaskRunnerDep,
    email_sender: EmailSenderDep,
) -> SendEmailVerificationOutput:
    """
    Sends an email verification email to the user by creating a new email verification action.
    This invalidates any existing pending email verification actions for the user.
    """
    logger.info("Task running in worker=%s", current_user.worker_id)

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

    verification_link_params = urlencode({"token": token, "action_id": str(action.id)})
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


# Register as background task
# ----------------------------------------------------------------------------------------------------------------------


@registry.background_task("send_email_verification")
async def run_task_in_worker(
    task_input: SendEmailVerificationInput,
    current_user: CurrentWorkerDep,
    settings: SettingsWorkerDep,
    db: DbWorkerDep,
    email_sender: EmailSenderWorkerDep,
) -> SendEmailVerificationOutput:
    return await send_email_verification(
        task_input, current_user=current_user, db=db, settings=settings, email_sender=email_sender
    )


SendEmailVerificationTaskDep = Annotated[BackgroundTask, Depends(run_task_in_worker)]
