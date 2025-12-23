"""
This module defines custom exception handlers for the FastAPI application.
Currently, it includes a handler for HTTP exceptions that logs server errors.
"""

from collections import defaultdict
import logging
from typing import Callable
from fastapi import FastAPI, Request, status
from fastapi.exception_handlers import http_exception_handler
from starlette.exceptions import HTTPException


logger = logging.getLogger(__name__)

# Custom handlers for HTTP exceptions that logs server errors.
# ----------------------------------------------------------------------------------------------------------------------


async def custom_http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR:
        logger.error("server error", extra={"path": request.url.path}, exc_info=exc)
    return await http_exception_handler(request, exc)


async def custom_exception_handler(request: Request, exc: Exception):
    logger.error("server error", extra={"path": request.url.path}, exc_info=exc)
    exc = HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")
    return await http_exception_handler(request, exc)


# Register the custom exception handlers with the FastAPI application.
# ----------------------------------------------------------------------------------------------------------------------


def register_exception_handlers(app: FastAPI):
    app.exception_handler(HTTPException)(custom_http_exception_handler)
    app.exception_handler(Exception)(custom_exception_handler)


# Decorator to collect possible HTTP exceptions for documentation.
# ----------------------------------------------------------------------------------------------------------------------

possible_common_causes = {
    status.HTTP_400_BAD_REQUEST: "The request contained invalid parameters.",
    status.HTTP_401_UNAUTHORIZED: "Credentials were missing or invalid.",
    status.HTTP_403_FORBIDDEN: "User is not authorized to perform the requested action.",
    status.HTTP_404_NOT_FOUND: "The requested resource could not be found.",
    status.HTTP_429_TOO_MANY_REQUESTS: "User has exceeded their rate limit.",
}


def raises(status_code: int, reason: str | None = None):
    """Decorator to collect possible HTTP exceptions for documentation."""

    def wrapper(func: Callable):
        description = reason or possible_common_causes.get(status_code) or "string"
        raising_causes: dict[int, list[str]] = getattr(func, "__raises__", defaultdict(list))
        raising_causes[status_code].append(description)
        setattr(func, "__raises__", raising_causes)
        return func

    return wrapper
