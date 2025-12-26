from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import pytest

from app.conftest import NoOpBackground
from app.features.users.models.user import User
from app.fixtures.user_factory import UserFactory
from app.main import app

client = TestClient(app)
url = "/api/auth/register"


@pytest.mark.asyncio
async def test_user_can_register_with_valid_data(db_fixture: AsyncSession, background_fixture: NoOpBackground):
    user_data = {
        "username": "newuser",
        "first_name": "New",
        "last_name": "User",
        "password": "newpassword",
        "email": "newuser@example.com",
    }
    response = client.post(url, json=user_data)
    assert response.status_code == 201

    data = response.json()
    assert data["user"]["username"] == user_data["username"]
    assert data["user"]["first_name"] == user_data["first_name"]
    assert data["user"]["last_name"] == user_data["last_name"]

    stmt = select(User).where(User.username == user_data["username"])
    result = await db_fixture.execute(stmt)
    user = result.scalar_one_or_none()
    assert user is not None
    assert user.check_password(user_data["password"])

    assert "send_email_verification_task" in background_fixture.called_tasks


@pytest.mark.asyncio
async def test_user_cannot_register_with_existing_username(db_fixture: AsyncSession):
    existing_user: User = UserFactory.build()
    db_fixture.add(existing_user)
    await db_fixture.commit()
    await db_fixture.refresh(existing_user)

    user_data = {
        "username": existing_user.username,
        "first_name": "Another",
        "last_name": "User",
        "password": "anotherpassword",
    }
    response = client.post(url, json=user_data)
    assert response.status_code == 400
    assert response.json()["type"] == "users/common/register/username-exists"


@pytest.mark.asyncio
async def test_user_cannot_register_with_existing_email(db_fixture: AsyncSession):
    existing_user: User = UserFactory.build(email="existing@example.com")
    db_fixture.add(existing_user)
    await db_fixture.commit()
    await db_fixture.refresh(existing_user)

    user_data = {
        "username": "uniqueusername",
        "first_name": "Another",
        "last_name": "User",
        "password": "anotherpassword",
        "email": "existing@example.com",
    }
    response = client.post(url, json=user_data)
    assert response.status_code == 400
    assert response.json()["type"] == "users/common/register/email-exists"
