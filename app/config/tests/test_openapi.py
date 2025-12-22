import pytest

from fastapi.testclient import TestClient
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
