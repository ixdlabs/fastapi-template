import logging

from app.config.background import periodic_task


logger = logging.getLogger(__name__)


def echo(message: str):
    logger.info("Echoing message", extra={"message": message})


# Task registration
# ----------------------------------------------------------------------------------------------------------------------


@periodic_task(10)
async def echo_task(message: str):
    echo(message)
