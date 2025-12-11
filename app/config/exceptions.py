from fastapi import Request
from fastapi.exception_handlers import http_exception_handler
from starlette.exceptions import HTTPException
import structlog


logger = structlog.get_logger()


async def custom_http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code >= 500:
        logger.error("server error", status_code=exc.status_code, path=request.url.path, detail=exc.detail)
    return await http_exception_handler(request, exc)
