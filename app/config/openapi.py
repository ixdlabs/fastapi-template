"""
This file is to customize the OpenAPI documentation interface.
It serves Scalar at /api/docs.

Scalara Docs: https://github.com/scalar/scalar <br/>
Approach: https://github.com/fastapi/fastapi/issues/1198#issuecomment-609019113
"""

import http
from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.openapi.utils import get_openapi
from starlette.routing import BaseRoute

from app.config.exceptions import ServiceException

router = APIRouter()


@router.get("/api/docs", response_class=HTMLResponse, include_in_schema=False)
async def scalar(request: Request):
    return """
<!doctype html>
<html>
  <head>
    <title>%s</title>
    <meta charset="utf-8" />
    <meta
      name="viewport"
      content="width=device-width, initial-scale=1" />
  </head>

  <body>
    <div id="app"></div>
    <script src="https://cdn.jsdelivr.net/npm/@scalar/api-reference"></script>
    <script>
      Scalar.createApiReference("#app", {
        url: "%s",
        "theme": "bluePlanet",
        persistAuth: true,
        tagsSorter: "alpha",
      })
    </script>
  </body>
</html>
    """ % (
        request.app.title,
        request.app.openapi_url,
    )


# Override FastAPI's default OpenAPI generation
# This adds RFC 7807 Problem Details for HTTP APIs documentation for custom exceptions
# ----------------------------------------------------------------------------------------------------------------------


def custom(app: FastAPI):
    """Override the default FastAPI OpenAPI generation to include custom exception documentation."""

    def wrapper() -> dict[str, object]:
        if app.openapi_schema:
            return app.openapi_schema

        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )

        # Fix for adding exception responses from @raises decorator
        for route in app.routes:
            if getattr(route, "include_in_schema", None):
                endpoint = getattr(route, "endpoint")
                raises: dict[int, list[type[ServiceException] | None]] = getattr(endpoint, "__raises__", {})
                for status_code, exceptions in raises.items():
                    exceptions = [exc for exc in exceptions if exc is not None]
                    add_service_exception_documentation(route, openapi_schema, status_code, exceptions)

        # Add security scope badges to operations
        for _, methods in openapi_schema["paths"].items():
            for _, operation in methods.items():
                operation_security = operation.get("security", [])
                if operation_security:
                    scopes: list[str] = []
                    for security_requirement in operation_security:
                        for scheme_key, scheme_scopes in dict(security_requirement).items():
                            for scheme_scope in scheme_scopes:
                                scopes.append(f"{scheme_key}:{scheme_scope}")
                    for scope in scopes:
                        if "x-badges" not in operation:
                            operation["x-badges"] = []
                        operation["x-badges"].append({"name": scope})

        app.openapi_schema = openapi_schema
        return app.openapi_schema

    return wrapper


def add_service_exception_documentation(
    route: BaseRoute, openapi_schema: dict[str, object], status_code: int, exceptions: list[type[ServiceException]]
):
    route_path: str = getattr(route, "path")
    route_methods: list[str] = getattr(route, "methods")
    route_methods = [method.lower() for method in route_methods]
    for method in route_methods:
        assert isinstance(openapi_schema["paths"], dict)
        assert isinstance(openapi_schema["paths"][route_path], dict)
        assert isinstance(openapi_schema["paths"][route_path][method], dict)
        assert isinstance(openapi_schema["paths"][route_path][method]["responses"], dict)
        if str(status_code) in openapi_schema["paths"][route_path][method]["responses"]:
            continue
        openapi_schema["paths"][route_path][method]["responses"][str(status_code)] = {
            "description": http.HTTPStatus(status_code).phrase,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string"},
                            "title": {"type": "string"},
                            "status": {"type": "integer"},
                            "detail": {"type": "string"},
                            "trace_id": {"type": "string"},
                        },
                    },
                    "examples": {
                        exc.type: {
                            "value": exc.build_problem_details(),
                        }
                        for exc in exceptions
                    },
                },
            },
        }
