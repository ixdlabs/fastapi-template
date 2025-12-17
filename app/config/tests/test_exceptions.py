from fastapi import FastAPI, HTTPException
import pytest
from unittest.mock import ANY, MagicMock
from pytest import MonkeyPatch

from app.config.exceptions import register_exception_handlers
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
