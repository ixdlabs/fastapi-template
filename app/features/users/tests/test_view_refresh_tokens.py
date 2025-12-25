from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
import pytest

from app.config.auth import Authenticator, get_current_user
from app.features.users.models import User
from app.features.users.tests.fixtures import UserFactory
from app.main import app

client = TestClient(app)


@pytest.mark.asyncio
async def test_user_can_refresh_token_with_valid_token(db_fixture: AsyncSession, authenticator_fixture: Authenticator):
    user: User = UserFactory.build(password__raw="testpassword")
    db_fixture.add(user)
    await db_fixture.commit()
    await db_fixture.refresh(user)

    access_token, refresh_token = authenticator_fixture.encode(user)
    response = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data

    verified_user = get_current_user(data["access_token"], authenticator_fixture)
    assert verified_user.id == user.id

    assert authenticator_fixture.sub(data["access_token"]) == user.id
    assert authenticator_fixture.sub(data["refresh_token"]) == user.id


@pytest.mark.asyncio
async def test_user_can_not_refresh_token_with_invalid_token(
    db_fixture: AsyncSession, authenticator_fixture: Authenticator
):
    response = client.post("/api/auth/refresh", json={"refresh_token": "invalid"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_raises_if_user_deleted(db_fixture: AsyncSession, authenticator_fixture: Authenticator):
    user: User = UserFactory.build(password__raw="testpassword")
    db_fixture.add(user)
    await db_fixture.commit()
    await db_fixture.refresh(user)

    access_token, refresh_token = authenticator_fixture.encode(user)
    await db_fixture.delete(user)
    await db_fixture.commit()

    response = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 401
