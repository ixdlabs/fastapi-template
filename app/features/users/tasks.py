import uuid

from sqlalchemy import select
import structlog
from app.config.database import get_db
from app.config.settings import get_settings
from app.config.background import background_task, periodic_task
from app.features.users.models import User


logger = structlog.get_logger()


@background_task
async def send_welcome_email(user_id: uuid.UUID):
    settings = get_settings()
    async with get_db(settings) as db:
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None:
            logger.error("User not found", user_id=user_id)
            return


@periodic_task(schedule=10)
async def echo_heartbeat():
    logger.info("Heartbeat task executed")
