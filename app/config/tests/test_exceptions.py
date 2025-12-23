from collections import defaultdict
from fastapi import FastAPI, HTTPException, status
import pytest
from unittest.mock import ANY, MagicMock
from pytest import MonkeyPatch

from app.config.exceptions import raises, register_exception_handlers
from fastapi.testclient import TestClient


@pytest.fixture
def test_app():
    app = FastAPI()

    register_exception_handlers(app)

    @app.get("/server-error")
    async def raise_server_error():
        raise HTTPException(status_code=500, detail="Internal Server Error")

    @app.get("/client-error")
    async def raise_client_error():
        raise HTTPException(status_code=404, detail="Not Found")

    @app.get("/unexpected-error")
    async def raise_unexpected_error():
        _ = 1 / 0

    return app


@pytest.mark.asyncio
async def test_custom_http_exception_handler_logs_server_error(test_app: FastAPI, monkeypatch: MonkeyPatch):
    mock_logger = MagicMock()
    monkeypatch.setattr("app.config.exceptions.logger.error", mock_logger)

    client = TestClient(test_app)
    response = client.get("/server-error")

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal Server Error"}
    mock_logger.assert_called_once_with("server error", extra={"path": "/server-error"}, exc_info=ANY)


@pytest.mark.asyncio
async def test_custom_http_exception_handler_ignores_client_error_logging(test_app):
    client = TestClient(test_app)
    response = client.get("/client-error")

    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}


@pytest.mark.asyncio
async def test_custom_exception_handler_logs_unexpected_error(test_app: FastAPI, monkeypatch: MonkeyPatch):
    mock_logger = MagicMock()
    monkeypatch.setattr("app.config.exceptions.logger.error", mock_logger)

    client = TestClient(test_app)
    with pytest.raises(ZeroDivisionError):
        client.get("/unexpected-error")

    mock_logger.assert_called_once_with("server error", extra={"path": "/unexpected-error"}, exc_info=ANY)


# Raises decorator tests
# ----------------------------------------------------------------------------------------------------------------------


def test_raises_adds_metadata_to_function():
    @raises(status.HTTP_400_BAD_REQUEST)
    def foo():
        pass

    assert hasattr(foo, "__raises__")
    assert isinstance(foo.__raises__, dict)
    assert status.HTTP_400_BAD_REQUEST in foo.__raises__


def test_raises_uses_explicit_reason_when_provided():
    @raises(status.HTTP_400_BAD_REQUEST, reason="Custom reason")
    def foo():
        pass

    assert foo.__raises__[status.HTTP_400_BAD_REQUEST] == ["Custom reason"]


def test_raises_uses_common_cause_when_reason_not_provided():
    @raises(status.HTTP_404_NOT_FOUND)
    def foo():
        pass

    assert foo.__raises__[status.HTTP_404_NOT_FOUND] == ["The requested resource could not be found."]


def test_raises_falls_back_to_string_when_no_common_cause_exists():
    @raises(418)  # I'm a teapot (not in possible_common_causes)
    def foo():
        pass

    assert foo.__raises__[418] == ["string"]


def test_raises_accumulates_multiple_status_codes():
    @raises(status.HTTP_400_BAD_REQUEST)
    @raises(status.HTTP_401_UNAUTHORIZED)
    def foo():
        pass

    assert set(foo.__raises__.keys()) == {status.HTTP_400_BAD_REQUEST, status.HTTP_401_UNAUTHORIZED}


def test_raises_accumulates_multiple_reasons_for_same_status_code():
    @raises(status.HTTP_400_BAD_REQUEST, reason="Reason one")
    @raises(status.HTTP_400_BAD_REQUEST, reason="Reason two")
    def foo():
        pass

    assert foo.__raises__[status.HTTP_400_BAD_REQUEST] == ["Reason two", "Reason one"]


def test_raises_preserves_existing_raises_metadata():
    def foo():
        pass

    existing_reason_default_dict = defaultdict(list)
    existing_reason_default_dict[status.HTTP_403_FORBIDDEN].append("Existing reason")
    setattr(foo, "__raises__", existing_reason_default_dict)
    decorated = raises(status.HTTP_404_NOT_FOUND)(foo)
    decorated_raises = getattr(decorated, "__raises__", {})
    assert decorated_raises[status.HTTP_403_FORBIDDEN] == ["Existing reason"]
    assert decorated_raises[status.HTTP_404_NOT_FOUND] == ["The requested resource could not be found."]


def test_raises_returns_same_function_object():
    def foo():
        pass

    decorated = raises(status.HTTP_400_BAD_REQUEST)(foo)
    assert decorated is foo
