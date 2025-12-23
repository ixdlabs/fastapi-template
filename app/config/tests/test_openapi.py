from http import HTTPStatus
from unittest.mock import MagicMock
from fastapi import FastAPI, status
from fastapi.openapi.utils import get_openapi
from fastapi.routing import BaseRoute
import pytest

from fastapi.testclient import TestClient
from app.config import openapi
from app.config.exceptions import raises
from app.main import app

client = TestClient(app)


@pytest.mark.asyncio
async def test_openapi_schema_endpoint_returns_200():
    response = client.get("/api/openapi.json")
    assert response.status_code == 200
    assert "openapi" in response.json()


@pytest.mark.asyncio
async def test_apidoc_endpoint_returns_200():
    response = client.get("/api/docs")
    assert response.status_code == 200


# OpenAPI custom method tests
# ----------------------------------------------------------------------------------------------------------------------


@pytest.fixture
def app_fixture():
    app = FastAPI()

    @app.get("/items")
    def get_items():
        return "items"

    assert get_items() == "items"
    return app


def test_add_route_response_adds_new_response(app_fixture: FastAPI):
    openapi_schema = get_openapi(title=app_fixture.title, version=app_fixture.version, routes=app_fixture.routes)
    route: BaseRoute = next(r for r in app_fixture.routes if getattr(r, "path") == "/items")
    openapi.add_route_response(route, openapi_schema=openapi_schema, status_code=404, descriptions=["Not found"])
    response = openapi_schema["paths"]["/items"]["get"]["responses"]["404"]

    assert response["description"] == HTTPStatus.NOT_FOUND.phrase
    assert response["content"]["application/json"]["schema"]["properties"]["detail"]["type"] == "string"
    assert "Not found" in response["content"]["application/json"]["examples"]
    assert response["content"]["application/json"]["examples"]["Not found"]["value"] == {"detail": "Not found"}


def test_add_route_response_does_not_override_existing_response(app_fixture: FastAPI):
    openapi_schema = get_openapi(title=app_fixture.title, version=app_fixture.version, routes=app_fixture.routes)
    route: BaseRoute = next(r for r in app_fixture.routes if getattr(r, "path") == "/items")
    openapi_schema["paths"]["/items"]["get"]["responses"]["404"] = {"description": "Existing"}
    openapi.add_route_response(
        route=route, openapi_schema=openapi_schema, status_code=404, descriptions=["New description"]
    )

    assert openapi_schema["paths"]["/items"]["get"]["responses"]["404"]["description"] == "Existing"


def test_custom_returns_cached_openapi_schema():
    app = FastAPI()
    app.openapi_schema = {"cached": True}
    result = openapi.custom(app)()
    assert result == {"cached": True}


def test_custom_adds_raises_metadata_to_openapi():
    app = FastAPI()

    @raises(status.HTTP_404_NOT_FOUND, reason="Not found")
    @raises(status.HTTP_404_NOT_FOUND)
    @app.get("/items")
    def get_items():
        return "items"

    assert get_items() == "items"

    schema = openapi.custom(app)()
    responses = schema["paths"]["/items"]["get"]["responses"]
    assert "404" in responses
    assert "Not found" in responses["404"]["content"]["application/json"]["examples"]


def test_custom_ignores_routes_not_in_schema():
    app = FastAPI()

    @raises(status.HTTP_400_BAD_REQUEST, reason="Bad request")
    @app.get("/hidden", include_in_schema=False)
    def hidden():
        return "hidden"

    assert hidden() == "hidden"

    schema = openapi.custom(app)()
    assert "/hidden" not in schema["paths"]


def test_custom_calls_add_route_response(monkeypatch):
    app = FastAPI()

    @raises(status.HTTP_400_BAD_REQUEST, reason="Bad request")
    @app.get("/items")
    def get_items():
        return "items"

    assert get_items() == "items"

    spy = MagicMock()
    monkeypatch.setattr("app.config.openapi.add_route_response", spy)
    openapi.custom(app)()
    spy.assert_called_once()
