import logging
from app.config.background import shared_async_task
from app.config.database import get_db
from app.config.settings import get_settings
from app.features.users.services.send_email_verification_email import (
    SendEmailVerificationInput,
    send_email_verification_email,
)
from app.features.users.services.send_password_reset_email import SendPasswordResetInput, send_password_reset_email


logger = logging.getLogger(__name__)


@shared_async_task("send_email_verification_email")
async def send_email_verification_email_task(raw_task_input: str):
    logger.info("Starting send_email_verification_email_task")
    settings = get_settings()
    async with get_db(settings) as db:
        task_input = SendEmailVerificationInput.model_validate_json(raw_task_input)
        result = await send_email_verification_email(task_input=task_input, settings=settings, db=db)
        return result.model_dump_json()


@shared_async_task("send_password_reset_email")
async def send_password_reset_email_task(raw_task_input: str):
    logger.info("Starting send_password_reset_email_task")
    settings = get_settings()
    async with get_db(settings) as db:
        task_input = SendPasswordResetInput.model_validate_json(raw_task_input)
        result = await send_password_reset_email(task_input=task_input, settings=settings, db=db)
        return result.model_dump_json()


@shared_async_task("echo_task")
async def echo_task():
    logger.info("Echo task executed")
