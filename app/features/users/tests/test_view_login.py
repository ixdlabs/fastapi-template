from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
import pytest

from app.config.settings import Settings
from app.config.auth import get_current_user
from app.features.users.models import User
from app.features.users.tests.fixtures import UserFactory
from app.main import app

client = TestClient(app)


@pytest.mark.asyncio
async def test_user_can_not_login_with_invalid_username():
    response = client.post("/api/v1/auth/login", json={"username": "invaliduser", "password": "testpassword"})
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid username or password"}


@pytest.mark.asyncio
async def test__user_can_not_login_with_invalid_password(db_fixture: AsyncSession):
    user: User = UserFactory.build(password__raw="correctpassword")
    db_fixture.add(user)
    await db_fixture.commit()
    await db_fixture.refresh(user)

    response = client.post("/api/v1/auth/login", json={"username": user.username, "password": "wrongpassword"})
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid username or password"}


@pytest.mark.asyncio
async def test_user_can_login_with_valid_credentials(db_fixture: AsyncSession, settings_fixture: Settings):
    user: User = UserFactory.build(password__raw="correctpassword")
    db_fixture.add(user)
    await db_fixture.commit()
    await db_fixture.refresh(user)

    response = client.post("/api/v1/auth/login", json={"username": user.username, "password": "correctpassword"})
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["id"] == str(user.id)
    assert data["user"]["username"] == user.username
    assert data["user"]["first_name"] == user.first_name
    assert data["user"]["last_name"] == user.last_name

    assert "access_token" in data
    verified_user = await get_current_user(data["access_token"], settings_fixture, db_fixture)
    assert verified_user.id == user.id


@pytest.mark.asyncio
async def test_user_cannot_login_with_oauth2_invalid_password(db_fixture: AsyncSession):
    user: User = UserFactory.build(password__raw="correctpassword")
    db_fixture.add(user)
    await db_fixture.commit()
    await db_fixture.refresh(user)

    response = client.post("/api/v1/auth/oauth2/token", data={"username": "testuser", "password": "testpassword"})
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid username or password"}


@pytest.mark.asyncio
async def test_user_can_login_with_oauth2_token_endpoint(db_fixture: AsyncSession):
    user: User = UserFactory.build(password__raw="correctpassword")
    db_fixture.add(user)
    await db_fixture.commit()
    await db_fixture.refresh(user)

    response = client.post("/api/v1/auth/oauth2/token", data={"username": user.username, "password": "correctpassword"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
