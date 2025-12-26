from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
import pytest

from app.config.auth import Authenticator, get_current_user
from app.features.users.models.user import User
from app.fixtures.user_factory import UserFactory
from app.main import app

client = TestClient(app)
url = "/api/auth/login"


@pytest.mark.asyncio
async def test_user_cannot_login_with_invalid_username():
    response = client.post(url, json={"username": "invaliduser", "password": "testpassword"})
    assert response.status_code == 401
    assert response.json()["type"] == "users/common/login/invalid-credentials"


@pytest.mark.asyncio
async def test__user_cannot_login_with_invalid_password(db_fixture: AsyncSession):
    user: User = UserFactory.build(password__raw="correctpassword")
    db_fixture.add(user)
    await db_fixture.commit()
    await db_fixture.refresh(user)

    response = client.post(url, json={"username": user.username, "password": "wrongpassword"})
    assert response.status_code == 401
    assert response.json()["type"] == "users/common/login/invalid-credentials"


@pytest.mark.asyncio
async def test_user_can_login_with_valid_credentials(db_fixture: AsyncSession, authenticator_fixture: Authenticator):
    user: User = UserFactory.build(password__raw="correctpassword")
    db_fixture.add(user)
    await db_fixture.commit()
    await db_fixture.refresh(user)

    response = client.post(url, json={"username": user.username, "password": "correctpassword"})
    assert response.status_code == 200

    data = response.json()
    assert data["user"]["id"] == str(user.id)
    assert data["user"]["username"] == user.username
    assert data["user"]["first_name"] == user.first_name
    assert data["user"]["last_name"] == user.last_name
    assert "access_token" in data
    verified_user = get_current_user(data["access_token"], authenticator_fixture)
    assert verified_user.id == user.id
