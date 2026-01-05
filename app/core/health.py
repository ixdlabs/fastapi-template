import logging
from fastapi import APIRouter
from pydantic import AwareDatetime, BaseModel
from sqlalchemy import text
from celery import current_app

from app.core.cache import CacheDep
from app.core.database import DbDep
from app.core.exceptions import ServiceException, raises
from app.core.timezone import utc_now

logger = logging.getLogger(__name__)

router = APIRouter()

# Input/Output models
# ----------------------------------------------------------------------------------------------------------------------


class HealthLivelinessResponseModel(BaseModel):
    status: str = "ok"


class HealthReadinessCheckResponseModel(BaseModel):
    status: str = "ok"
    last_check: AwareDatetime


# Exceptions
# ----------------------------------------------------------------------------------------------------------------------


class DbServiceUnavailableException(ServiceException):
    status_code = 503
    type = "core/health/db-service-unavailable"
    detail = "Database service is unavailable"


class BackgroundWorkersUnavailableException(ServiceException):
    status_code = 503
    type = "core/health/background-workers-unavailable"
    detail = "Background workers are unavailable"


# Endpoint
# ----------------------------------------------------------------------------------------------------------------------


@router.get("/health/live")
async def health_liveliness_check() -> HealthLivelinessResponseModel:
    """Liveliness check endpoint to verify the service is running."""
    return HealthLivelinessResponseModel()


@raises(DbServiceUnavailableException)
@raises(BackgroundWorkersUnavailableException)
@router.get("/health/ready")
async def health_readiness_check(db: DbDep, cache: CacheDep) -> HealthReadinessCheckResponseModel:
    """Health check endpoint to verify the service is operational."""
    response_cache = cache.vary_on_path().with_ttl(30).build(HealthReadinessCheckResponseModel)
    if cached_response := await response_cache.get():
        return cached_response

    # Check DB connectivity
    try:
        _ = await db.execute(text("SELECT 1"))
    except Exception as e:
        raise DbServiceUnavailableException() from e

    # Check Celery connectivity
    if not current_app.conf.task_always_eager:
        pongs = current_app.control.ping(timeout=3)
        if not pongs:
            raise BackgroundWorkersUnavailableException()

    return await response_cache.set(HealthReadinessCheckResponseModel(last_check=utc_now()))
