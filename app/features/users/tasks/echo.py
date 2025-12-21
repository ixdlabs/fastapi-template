import logging

from app.config.background import shared_async_task


logger = logging.getLogger(__name__)


def echo(message: str):
    logger.info("Echoing message", extra={"message": message})


# Task registration
# ----------------------------------------------------------------------------------------------------------------------


@shared_async_task("echo_task")
async def echo_task(message: str):
    echo(message)
