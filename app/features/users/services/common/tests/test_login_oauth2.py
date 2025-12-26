from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
import pytest

from app.features.users.models.user import User
from app.fixtures.user_factory import UserFactory
from app.main import app

client = TestClient(app)
url = "/api/auth/oauth2/token"


@pytest.mark.asyncio
async def test_user_cannot_login_with_oauth2_invalid_username(db_fixture: AsyncSession):
    user: User = UserFactory.build(password__raw="correctpassword")
    db_fixture.add(user)
    await db_fixture.commit()
    await db_fixture.refresh(user)

    response = client.post(url, data={"username": "testuser", "password": "testpassword"})
    assert response.status_code == 401
    assert response.json()["type"] == "users/common/login-oauth2/invalid-credentials"


@pytest.mark.asyncio
async def test_user_cannot_login_with_oauth2_invalid_password(db_fixture: AsyncSession):
    user: User = UserFactory.build(password__raw="correctpassword", username="testuser")
    db_fixture.add(user)
    await db_fixture.commit()
    await db_fixture.refresh(user)

    response = client.post(url, data={"username": "testuser", "password": "testpassword"})
    assert response.status_code == 401
    assert response.json()["type"] == "users/common/login-oauth2/invalid-credentials"


@pytest.mark.asyncio
async def test_user_can_login_with_oauth2_token_endpoint(db_fixture: AsyncSession):
    user: User = UserFactory.build(password__raw="correctpassword")
    db_fixture.add(user)
    await db_fixture.commit()
    await db_fixture.refresh(user)

    response = client.post(url, data={"username": user.username, "password": "correctpassword"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
