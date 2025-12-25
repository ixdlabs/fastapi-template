from http import HTTPStatus
from unittest.mock import MagicMock
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.routing import BaseRoute
import pytest

from fastapi.testclient import TestClient
from app.config import openapi
from app.config.exceptions import ServiceException, raises
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
    test_app = FastAPI()

    @test_app.get("/items")
    def get_items():
        return "items"

    assert get_items() == "items"
    return test_app


class SampleException(ServiceException):
    status_code = 400
    type = "sample/error"
    detail = "This is a sample error"


def test_add_service_exception_documentation_adds_new_response(app_fixture: FastAPI):
    openapi_schema = get_openapi(title=app_fixture.title, version=app_fixture.version, routes=app_fixture.routes)
    route: BaseRoute = next(r for r in app_fixture.routes if getattr(r, "path") == "/items")
    openapi.add_service_exception_documentation(route, openapi_schema, status_code=400, exceptions=[SampleException])
    response = openapi_schema["paths"]["/items"]["get"]["responses"]["400"]

    assert response["description"] == HTTPStatus.BAD_REQUEST.phrase
    assert response["content"]["application/json"]["schema"]["properties"]["detail"]["type"] == "string"
    assert "sample/error" in response["content"]["application/json"]["examples"]
    assert response["content"]["application/json"]["examples"]["sample/error"]["value"]["type"] == "sample/error"


def test_add_service_exception_documentation_does_not_override_existing_response(app_fixture: FastAPI):
    openapi_schema = get_openapi(title=app_fixture.title, version=app_fixture.version, routes=app_fixture.routes)
    route: BaseRoute = next(r for r in app_fixture.routes if getattr(r, "path") == "/items")
    openapi_schema["paths"]["/items"]["get"]["responses"]["400"] = {"description": "Existing"}
    openapi.add_service_exception_documentation(route, openapi_schema, status_code=400, exceptions=[SampleException])

    assert openapi_schema["paths"]["/items"]["get"]["responses"]["400"]["description"] == "Existing"


def test_custom_returns_cached_openapi_schema():
    test_app = FastAPI()
    test_app.openapi_schema = {"cached": True}
    result = openapi.custom(test_app)()
    assert result == {"cached": True}


def test_custom_adds_raises_metadata_to_openapi():
    test_app = FastAPI()

    @raises(SampleException)
    @test_app.get("/items")
    def get_items():
        return "items"

    assert get_items() == "items"

    schema = openapi.custom(test_app)()
    responses = schema["paths"]["/items"]["get"]["responses"]
    assert "400" in responses
    assert "sample/error" in responses["400"]["content"]["application/json"]["examples"]


def test_custom_ignores_routes_not_in_schema():
    test_app = FastAPI()

    @raises(SampleException)
    @test_app.get("/hidden", include_in_schema=False)
    def hidden():
        return "hidden"

    assert hidden() == "hidden"

    schema = openapi.custom(test_app)()
    assert "/hidden" not in schema["paths"]


def test_custom_calls_add_service_exception_documentation(monkeypatch):
    test_app = FastAPI()

    @raises(SampleException)
    @test_app.get("/items")
    def get_items():
        return "items"

    assert get_items() == "items"

    spy = MagicMock()
    monkeypatch.setattr("app.config.openapi.add_service_exception_documentation", spy)
    openapi.custom(test_app)()
    spy.assert_called_once()
