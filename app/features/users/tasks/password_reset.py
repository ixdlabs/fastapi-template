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


class SendPasswordResetInput(BaseModel):
    user_id: uuid.UUID
    email: EmailStr


async def send_password_reset_email(task_input: SendPasswordResetInput, settings: SettingsDep, db: DbDep):
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


# Task registration
# ----------------------------------------------------------------------------------------------------------------------


@shared_async_task("send_password_reset_email")
async def send_password_reset_email_task(raw_task_input: str):
    settings = get_settings()
    async with get_db(settings) as db:
        task_input = SendPasswordResetInput.model_validate_json(raw_task_input)
        await send_password_reset_email(task_input=task_input, settings=settings, db=db)
