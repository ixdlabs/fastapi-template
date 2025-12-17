"""
This module defines custom exception handlers for the FastAPI application.
Currently, it includes a handler for HTTP exceptions that logs server errors.
"""

import logging
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
