from fastapi.testclient import TestClient
import pytest

from app.main import app

client = TestClient(app)


@pytest.mark.asyncio
async def test_invalid_username_cannot_login():
    response = client.post("/api/v1/auth/login", json={"username": "invaliduser", "password": "testpassword"})
    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid username or password"}
