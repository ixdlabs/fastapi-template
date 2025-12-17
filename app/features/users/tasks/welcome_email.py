import uuid
from pydantic import BaseModel
from sqlalchemy import select
import structlog

from app.config.background import background_task
from app.config.database import DbDep, get_db
from app.config.settings import get_settings
from app.features.users.models import User


logger = structlog.get_logger()


class WelcomeEmailInput(BaseModel):
    user_id: uuid.UUID


async def send_welcome_email(input: WelcomeEmailInput, db: DbDep):
    stmt = select(User).where(User.id == input.user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        logger.error("User not found", user_id=input.user_id)
        return


# Task registration
# ----------------------------------------------------------------------------------------------------------------------


@background_task
async def send_welcome_email_task(user_id: uuid.UUID):
    settings = get_settings()
    async with get_db(settings) as db:
        await send_welcome_email(input=WelcomeEmailInput(user_id=user_id), db=db)
