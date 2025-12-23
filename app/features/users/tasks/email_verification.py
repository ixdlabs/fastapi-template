from datetime import datetime, timedelta
import logging
import uuid
from pydantic import BaseModel, EmailStr
from sqlalchemy import update

from app.config.background import shared_async_task
from app.config.database import DbDep, get_db
from app.config.settings import SettingsDep, get_settings
from app.features.users.models import UserEmailVerification, UserEmailVerificationState


logger = logging.getLogger(__name__)


class SendEmailVerificationInput(BaseModel):
    user_id: uuid.UUID
    email: EmailStr


async def send_email_verification_email(input: SendEmailVerificationInput, settings: SettingsDep, db: DbDep):
    expiration = datetime.now() + timedelta(minutes=settings.email_verification_expiration_minutes)
    token = str(uuid.uuid4())

    update_stmt = (
        update(UserEmailVerification)
        .where(UserEmailVerification.user_id == input.user_id)
        .where(UserEmailVerification.state == UserEmailVerificationState.PENDING)
        .values(state=UserEmailVerificationState.OBSELETE)
    )
    await db.execute(update_stmt)

    verification = UserEmailVerification(user_id=input.user_id, email=input.email, expires_at=expiration)
    verification.set_verification_token(token)
    db.add(verification)

    await db.commit()
    await db.refresh(verification)

    logger.info("Sending email verification email, id=%s, token=%s", verification.id, token)


# Task registration
# ----------------------------------------------------------------------------------------------------------------------


@shared_async_task("send_email_verification_email")
async def send_email_verification_email_task(raw_task_input: str):
    settings = get_settings()
    async with get_db(settings) as db:
        task_input = SendEmailVerificationInput.model_validate_json(raw_task_input)
        await send_email_verification_email(input=task_input, settings=settings, db=db)
