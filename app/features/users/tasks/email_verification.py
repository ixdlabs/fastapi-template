from datetime import datetime, timedelta, timezone
import logging
import uuid
from pydantic import BaseModel, EmailStr
from sqlalchemy import update

from app.config.background import shared_async_task
from app.config.database import DbDep, get_db
from app.config.settings import SettingsDep, get_settings
from app.features.users.models import UserAction, UserActionState, UserActionType


logger = logging.getLogger(__name__)


class SendEmailVerificationInput(BaseModel):
    user_id: uuid.UUID
    email: EmailStr


async def send_email_verification_email(task_input: SendEmailVerificationInput, settings: SettingsDep, db: DbDep):
    expiration = datetime.now(timezone.utc) + timedelta(minutes=settings.email_verification_expiration_minutes)
    token = str(uuid.uuid4())

    update_stmt = (
        update(UserAction)
        .where(UserAction.user_id == task_input.user_id)
        .where(UserAction.state == UserActionState.PENDING)
        .where(UserAction.type == UserActionType.EMAIL_VERIFICATION)
        .values(state=UserActionState.OBSOLETE)
    )
    await db.execute(update_stmt)

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

    logger.info("Sending email verification email, action_id=%s, token=%s", action.id, token)


# Task registration
# ----------------------------------------------------------------------------------------------------------------------


@shared_async_task("send_email_verification_email")
async def send_email_verification_email_task(raw_task_input: str):
    settings = get_settings()
    async with get_db(settings) as db:
        task_input = SendEmailVerificationInput.model_validate_json(raw_task_input)
        await send_email_verification_email(task_input=task_input, settings=settings, db=db)
