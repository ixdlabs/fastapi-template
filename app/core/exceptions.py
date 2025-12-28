"""
This module defines custom exception handlers for the FastAPI application.
Currently, it includes a handler for HTTP exceptions that logs server errors.
"""

import abc
from collections import defaultdict
from collections.abc import Callable
import logging
from typing import ParamSpec, TypeVar
from opentelemetry import trace
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
import http
from fastapi.exception_handlers import http_exception_handler
from starlette.exceptions import HTTPException


tracer = trace.get_tracer(__name__)
logger = logging.getLogger(__name__)


# Base Service Exception class implementing RFC 7807 error response format.
# RFC: https://datatracker.ietf.org/doc/html/rfc7807
# ----------------------------------------------------------------------------------------------------------------------


class ServiceException(abc.ABC, HTTPException):
    status_code: int
    type: str
    detail: str

    def __init__(self, headers: dict[str, str] | None = None) -> None:
        super().__init__(status_code=self.status_code, detail=self.detail, headers=headers)

    def to_rfc7807(self) -> dict[str, object]:
        with tracer.start_as_current_span("rfc7807") as span:
            return self.build_problem_details(trace_id=f"{span.get_span_context().trace_id:032x}")

    @classmethod
    def build_problem_details(cls, trace_id: str = "00000000000000000000000000000000") -> dict[str, object]:
        """Build a RFC 7807 compliant problem details dictionary."""
        http_status = http.HTTPStatus(cls.status_code)
        return {
            "type": cls.type or "about:blank",
            "title": http_status.phrase,
            "status": cls.status_code,
            "detail": cls.detail or http_status.description,
            "trace_id": trace_id,
        }


# Custom handlers for HTTP exceptions that logs server errors.
# ----------------------------------------------------------------------------------------------------------------------


async def custom_http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR:
        logger.error("server error", extra={"path": request.url.path}, exc_info=exc)
    if isinstance(exc, ServiceException):
        return JSONResponse(exc.to_rfc7807(), status_code=exc.status_code, headers=exc.headers)
    return await http_exception_handler(request, exc)


async def custom_exception_handler(request: Request, exc: Exception):
    logger.error("server error", extra={"path": request.url.path}, exc_info=exc)
    exc = HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")
    return await http_exception_handler(request, exc)


# Register the custom exception handlers with the FastAPI application.
# ----------------------------------------------------------------------------------------------------------------------


def register_exception_handlers(app: FastAPI):
    _ = app.exception_handler(HTTPException)(custom_http_exception_handler)
    _ = app.exception_handler(Exception)(custom_exception_handler)


# Decorator to collect possible HTTP exceptions for documentation.
# ----------------------------------------------------------------------------------------------------------------------

P = ParamSpec("P")
R = TypeVar("R")


def raises(exc: type[ServiceException]):
    """
    Decorator to collect possible HTTP exceptions for documentation.

    The decorator should come before the HTTP method decorator (e.g., `@router.get`).
    Eg:
    ```python
    @raises(SomeException)
    @router.get("/")
    def some_route(...):
        ...
    ```
    """

    def wrapper(func: Callable[P, R]) -> Callable[P, R]:
        raising_causes: dict[int, list[type[ServiceException]]] = getattr(
            func, "__raised_service_exceptions", defaultdict(list)
        )
        raising_causes[exc.status_code].append(exc)
        setattr(func, "__raised_service_exceptions", raising_causes)
        return func

    return wrapper
