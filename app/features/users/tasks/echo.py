import structlog

from app.config.background import periodic_task


logger = structlog.get_logger()


def echo(message: str):
    logger.info("Echoing message", message=message)


# Task registration
# ----------------------------------------------------------------------------------------------------------------------


@periodic_task(10)
async def echo_task(message: str):
    echo(message)
