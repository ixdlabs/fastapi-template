from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
import pytest

from app.features.users.models import User
from app.features.users.tests.fixtures import UserFactory
from app.main import app

client = TestClient(app)


@pytest.mark.asyncio
async def test_invalid_username_cannot_login():
    response = client.post("/api/v1/auth/login", json={"username": "invaliduser", "password": "testpassword"})
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid username or password"}


@pytest.mark.asyncio
async def test_invalid_password_cannot_login(db_fixture: AsyncSession):
    user: User = UserFactory.build()
    user.set_password("correctpassword")
    db_fixture.add(user)
    await db_fixture.commit()
    await db_fixture.refresh(user)

    response = client.post("/api/v1/auth/login", json={"username": user.username, "password": "wrongpassword"})
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid username or password"}


@pytest.mark.asyncio
async def test_valid_login_returns_token_and_user(db_fixture: AsyncSession):
    user: User = UserFactory.build()
    user.set_password("correctpassword")
    db_fixture.add(user)
    await db_fixture.commit()
    await db_fixture.refresh(user)

    response = client.post("/api/v1/auth/login", json={"username": user.username, "password": "correctpassword"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["id"] == str(user.id)
    assert data["user"]["username"] == user.username
    assert data["user"]["first_name"] == user.first_name
    assert data["user"]["last_name"] == user.last_name
