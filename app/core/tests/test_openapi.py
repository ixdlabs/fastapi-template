from http import HTTPStatus
from unittest.mock import MagicMock
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
import pytest

from fastapi.testclient import TestClient
from app.core import openapi
from app.core.exceptions import ServiceException, raises
from app.main import app
from pytest import MonkeyPatch

client = TestClient(app)


@pytest.mark.asyncio
async def test_openapi_endpoint_serves_schema_successfully():
    response = client.get("/api/openapi.json")
    assert response.status_code == 200
    assert "openapi" in response.json()


@pytest.mark.asyncio
async def test_apidoc_endpoint_serves_swagger_ui_successfully():
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


def test_add_service_exception_documentation_injects_exception_response_when_missing(app_fixture: FastAPI):
    openapi_schema = get_openapi(title=app_fixture.title, version=app_fixture.version, routes=app_fixture.routes)
    route = next(r for r in app_fixture.routes if getattr(r, "path") == "/items")
    openapi.add_service_exception_documentation(route, openapi_schema, status_code=400, exceptions=[SampleException])
    response = openapi_schema["paths"]["/items"]["get"]["responses"]["400"]

    assert response["description"] == HTTPStatus.BAD_REQUEST.phrase
    assert response["content"]["application/json"]["schema"]["properties"]["detail"]["type"] == "string"
    assert "sample/error" in response["content"]["application/json"]["examples"]
    assert response["content"]["application/json"]["examples"]["sample/error"]["value"]["type"] == "sample/error"


def test_add_service_exception_documentation_retains_existing_response(app_fixture: FastAPI):
    openapi_schema = get_openapi(title=app_fixture.title, version=app_fixture.version, routes=app_fixture.routes)
    route = next(r for r in app_fixture.routes if getattr(r, "path") == "/items")
    openapi_schema["paths"]["/items"]["get"]["responses"]["400"] = {"description": "Existing"}
    openapi.add_service_exception_documentation(route, openapi_schema, status_code=400, exceptions=[SampleException])

    assert openapi_schema["paths"]["/items"]["get"]["responses"]["400"]["description"] == "Existing"


def test_custom_openapi_builder_returns_existing_schema_when_cached():
    test_app = FastAPI()
    test_app.openapi_schema = {"cached": True}
    result = openapi.custom(test_app)()
    assert result == {"cached": True}


def test_custom_openapi_builder_includes_raises_metadata_in_schema():
    test_app = FastAPI()

    @raises(SampleException)
    @test_app.get("/items")
    def get_items():
        return "items"

    assert get_items() == "items"

    schema = openapi.custom(test_app)()
    assert isinstance(schema, dict)
    assert isinstance(schema["paths"], dict)
    responses = schema["paths"]["/items"]["get"]["responses"]
    assert "400" in responses
    assert "sample/error" in responses["400"]["content"]["application/json"]["examples"]


def test_custom_openapi_builder_skips_routes_excluded_from_schema():
    test_app = FastAPI()

    @raises(SampleException)
    @test_app.get("/hidden", include_in_schema=False)
    def hidden():
        return "hidden"

    assert hidden() == "hidden"

    schema = openapi.custom(test_app)()
    assert isinstance(schema, dict)
    assert isinstance(schema["paths"], dict)
    assert "/hidden" not in schema["paths"]


def test_custom_openapi_builder_calls_add_service_exception_documentation(monkeypatch: MonkeyPatch):
    test_app = FastAPI()

    @raises(SampleException)
    @test_app.get("/items")
    def get_items():
        return "items"

    assert get_items() == "items"

    spy = MagicMock()
    monkeypatch.setattr("app.core.openapi.add_service_exception_documentation", spy)
    _ = openapi.custom(test_app)()
    spy.assert_called_once()
