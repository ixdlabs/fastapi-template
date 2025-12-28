from fastapi import FastAPI, status
import pytest
from unittest.mock import ANY, MagicMock
from pytest import MonkeyPatch

from app.config.exceptions import ServiceException, raises, register_exception_handlers
from fastapi.testclient import TestClient


class Sample500Exception(ServiceException):
    status_code = 500
    type = "sample/500-error"
    detail = "This is a sample 500 error"


class Sample400Exception(ServiceException):
    status_code = 400
    type = "sample/400-error"
    detail = "This is a sample 400 error"


class Sample404Exception(ServiceException):
    status_code = 404
    type = "sample/404-error"
    detail = "This is a sample 404 error"


@pytest.fixture
def test_app():
    app = FastAPI()

    register_exception_handlers(app)

    @app.get("/server-error")
    async def _():
        raise Sample500Exception()

    @app.get("/client-error")
    async def _():
        raise Sample404Exception()

    @app.get("/unexpected-error")
    async def _():
        _ = 1 / 0

    return app


# Custom exception handler tests
# ----------------------------------------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_custom_http_exception_handler_logs_and_returns_registered_server_error(
    test_app: FastAPI, monkeypatch: MonkeyPatch
):
    mock_logger = MagicMock()
    monkeypatch.setattr("app.config.exceptions.logger.error", mock_logger)

    client = TestClient(test_app)
    response = client.get("/server-error")

    assert response.status_code == 500
    assert response.json()["detail"] == "This is a sample 500 error"
    mock_logger.assert_called_once_with("server error", extra={"path": "/server-error"}, exc_info=ANY)


@pytest.mark.asyncio
async def test_custom_http_exception_handler_returns_registered_client_error_without_logging(test_app: FastAPI):
    client = TestClient(test_app)
    response = client.get("/client-error")

    assert response.status_code == 404
    assert response.json()["detail"] == "This is a sample 404 error"


@pytest.mark.asyncio
async def test_custom_exception_handler_logs_unhandled_exceptions_as_server_error(
    test_app: FastAPI, monkeypatch: MonkeyPatch
):
    mock_logger = MagicMock()
    monkeypatch.setattr("app.config.exceptions.logger.error", mock_logger)

    client = TestClient(test_app)
    with pytest.raises(ZeroDivisionError):
        _ = client.get("/unexpected-error")

    mock_logger.assert_called_once_with("server error", extra={"path": "/unexpected-error"}, exc_info=ANY)


# Raises decorator tests
# ----------------------------------------------------------------------------------------------------------------------


def test_raises_decorator_attaches_exception_metadata_to_function():
    @raises(Sample400Exception)
    def foo():
        return 123

    assert foo() == 123
    assert hasattr(foo, "__raised_service_exceptions")
    raises_value = getattr(foo, "__raised_service_exceptions")
    assert isinstance(raises_value, dict)
    assert status.HTTP_400_BAD_REQUEST in raises_value
    assert raises_value[status.HTTP_400_BAD_REQUEST] == [Sample400Exception]


def test_raises_decorator_accumulates_multiple_status_codes():
    @raises(Sample400Exception)
    @raises(Sample404Exception)
    def foo():
        return 123

    assert foo() == 123
    raises_value = getattr(foo, "__raised_service_exceptions")
    assert isinstance(raises_value, dict)
    assert set(raises_value.keys()) == {status.HTTP_400_BAD_REQUEST, status.HTTP_404_NOT_FOUND}


def test_raises_decorator_returns_original_function_instance():
    def foo():
        return 123

    assert foo() == 123
    decorated = raises(Sample400Exception)(foo)
    assert decorated is foo
