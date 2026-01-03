from datetime import datetime, timezone
import logging
from typing import Annotated
import uuid
from fastapi import APIRouter, Depends
from pydantic import AwareDatetime, BaseModel
from sqlalchemy import text

from app.core.background import BackgroundTask, TaskRegistry
from app.core.cache import CacheDep
from app.core.database import DbDep
from app.core.exceptions import ServiceException, raises

logger = logging.getLogger(__name__)

router = APIRouter()
registry = TaskRegistry()

# Input/Output models
# ----------------------------------------------------------------------------------------------------------------------


class HealthCheckResponseModel(BaseModel):
    status: str = "ok"
    last_check: AwareDatetime


class PingCeleryInputModel(BaseModel):
    value: uuid.UUID


class PongCeleryOutputModel(BaseModel):
    value: uuid.UUID


# Exceptions
# ----------------------------------------------------------------------------------------------------------------------


class ServiceUnavailableException(ServiceException):
    status_code = 503
    type = "core/health/service-unavailable"
    detail = "Service Unavailable"


# Task
# ----------------------------------------------------------------------------------------------------------------------


@registry.background_task("ping_celery")
async def ping_celery(task_input: PingCeleryInputModel) -> PongCeleryOutputModel:
    """Ping task for testing celery worker connectivity."""
    return PongCeleryOutputModel(value=task_input.value)


PingCeleryTaskDep = Annotated[BackgroundTask, Depends(ping_celery)]


# Endpoint
# ----------------------------------------------------------------------------------------------------------------------


@raises(ServiceUnavailableException)
@router.get("/health")
async def health_check(db: DbDep, cache: CacheDep, ping_celery_task: PingCeleryTaskDep) -> HealthCheckResponseModel:
    """Health check endpoint to verify the service is operational."""
    response_cache = cache.vary_on_path().with_ttl(30).build(HealthCheckResponseModel)
    if cached_response := await response_cache.get():
        return cached_response

    # Check DB connectivity
    try:
        _ = await db.execute(text("SELECT 1"))
    except Exception as e:
        logger.error("Health check failed (database)", exc_info=e)
        raise ServiceUnavailableException() from e

    # Check Cache connectivity
    try:
        test_value = uuid.uuid4()
        test_cache = cache.with_key("health_check").with_ttl(10).build(str)
        _ = await test_cache.set(str(test_value))
        cached_value = await test_cache.get()
        if cached_value != str(test_value):
            raise AssertionError("Cached value does not match set value")
    except Exception as e:
        logger.error("Health check failed (cache)", exc_info=e)
        raise ServiceUnavailableException() from e

    # Check celery connectivity
    try:
        test_value = uuid.uuid4()
        await ping_celery_task.submit(PingCeleryInputModel(value=test_value))
        pong_output = await ping_celery_task.wait_and_get_result(PongCeleryOutputModel, timeout=5)
        if pong_output.value != test_value:
            raise AssertionError("Pong value does not match ping value")
    except Exception as e:
        logger.error("Health check failed (celery)", exc_info=e)
        raise ServiceUnavailableException() from e

    current_time = datetime.now(timezone.utc)
    return await response_cache.set(HealthCheckResponseModel(last_check=current_time))
