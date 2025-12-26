from datetime import datetime, timedelta, timezone
import logging
import uuid
from fastapi import APIRouter
from pydantic import BaseModel, EmailStr
from sqlalchemy import update

from app.config.auth import CurrentTaskRunnerDep
from app.config.database import DbDep
from app.config.settings import SettingsDep
from app.features.users.models.user_action import UserAction, UserActionState, UserActionType


logger = logging.getLogger(__name__)
router = APIRouter()


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


@router.post("/send-email-verification-email")
async def send_email_verification(
    task_input: SendEmailVerificationInput, current_user: CurrentTaskRunnerDep, settings: SettingsDep, db: DbDep
) -> SendEmailVerificationOutput:
    """
    Sends an email verification email to the user by creating a new email verification action.
    This invalidates any existing pending email verification actions for the user.
    """
    logger.info("Task initiated by runner_id=%s", current_user.id)

    # Invalidate existing pending email verification actions
    update_stmt = (
        update(UserAction)
        .where(UserAction.user_id == task_input.user_id)
        .where(UserAction.state == UserActionState.PENDING)
        .where(UserAction.type == UserActionType.EMAIL_VERIFICATION)
        .values(state=UserActionState.OBSOLETE)
    )
    await db.execute(update_stmt)

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
