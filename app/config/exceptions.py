"""
This module defines custom exception handlers for the FastAPI application.
Currently, it includes a handler for HTTP exceptions that logs server errors.
"""

from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from starlette.exceptions import HTTPException
import structlog


logger = structlog.get_logger()

# Custom handlers for HTTP exceptions that logs server errors.
# ----------------------------------------------------------------------------------------------------------------------


async def custom_http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code >= 500:
        logger.error("server error", status_code=exc.status_code, path=request.url.path, detail=exc.detail)
    return await http_exception_handler(request, exc)


# Register the custom exception handlers with the FastAPI application.
# ----------------------------------------------------------------------------------------------------------------------


def register_exception_handlers(app: FastAPI):
    app.exception_handler(HTTPException)(custom_http_exception_handler)
