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
from fastapi.routing import BaseRoute

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
      })
    </script>
  </body>
</html>
    """ % (
        request.app.title,
        request.app.openapi_url,
    )


def custom(app: FastAPI):
    """Override the default FastAPI OpenAPI generation to include custom exception documentation."""

    def wrapper() -> dict:
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
                raises: dict[int, list[str]] = getattr(endpoint, "__raises__", {})
                for status_code, descriptions in raises.items():
                    descriptions = [desc for desc in descriptions if desc is not None]
                    add_route_response(route, openapi_schema, status_code, descriptions)

        app.openapi_schema = openapi_schema
        return app.openapi_schema

    return wrapper


def add_route_response(route: BaseRoute, openapi_schema: dict, status_code: int, descriptions: list[str]):
    route_path: str = getattr(route, "path")
    route_methods: list[str] = getattr(route, "methods")
    route_methods = [method.lower() for method in route_methods]
    for method in route_methods:
        if str(status_code) in openapi_schema["paths"][route_path][method]["responses"]:
            continue
        openapi_schema["paths"][route_path][method]["responses"][str(status_code)] = {
            "description": http.HTTPStatus(status_code).phrase,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {"detail": {"type": "string"}},
                    },
                    "examples": {
                        desc: {
                            "value": {"detail": desc},
                        }
                        for desc in descriptions
                    },
                },
            },
        }
