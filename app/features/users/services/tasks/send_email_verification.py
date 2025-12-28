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
from app.core.settings import SettingsDep
from app.features.users.models.user_action import UserAction, UserActionState, UserActionType


logger = logging.getLogger(__name__)
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
    token: str


# Task/Endpoint implementation
# ----------------------------------------------------------------------------------------------------------------------


@router.post("/send-email-verification")
async def send_email_verification(
    task_input: SendEmailVerificationInput,
    *,
    db: DbDep,
    settings: SettingsDep,
    current_user: CurrentTaskRunnerDep,
    **kwargs: object,
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

    logger.info("Sending email verification, action_id=%s, token=%s", action.id, token)
    return SendEmailVerificationOutput(action_id=action.id, token=token)


send_email_verification_task = registry.register_background_task(send_email_verification)
SendEmailVerificationTaskDep = Annotated[BackgroundTask, Depends(send_email_verification_task)]
