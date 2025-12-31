import logging
from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from app.core.database import DbDep
from app.core.exceptions import ServiceException

logger = logging.getLogger(__name__)

router = APIRouter()

# Input/Output models
# ----------------------------------------------------------------------------------------------------------------------


class HealthCheckResponseModel(BaseModel):
    status: str = "ok"


# Exceptions
# ----------------------------------------------------------------------------------------------------------------------


class ServiceUnavailableException(ServiceException):
    status_code = 503
    type = "core/health/service-unavailable"
    detail = "Service Unavailable"


# Endpoint
# ----------------------------------------------------------------------------------------------------------------------


@router.get("/health", tags=["Health"])
async def health_check(db: DbDep) -> HealthCheckResponseModel:
    """Health check endpoint to verify the service is operational."""
    try:
        # Check DB connectivity
        _ = await db.execute(text("SELECT 1"))
    except Exception as e:
        logger.error("Health check failed", exc_info=e)
        raise ServiceUnavailableException() from e
    return HealthCheckResponseModel()
