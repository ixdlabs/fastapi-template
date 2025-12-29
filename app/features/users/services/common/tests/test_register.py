from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pytest import MonkeyPatch
import pytest

from app.features.users.models.user import User
from app.features.users.services.tasks.send_email_verification import SendEmailVerificationInput
from app.fixtures.user_factory import UserFactory

URL = "/api/auth/register"


@pytest.mark.asyncio
async def test_user_can_register_with_valid_data(
    test_client_fixture: TestClient, db_fixture: AsyncSession, monkeypatch: MonkeyPatch
):
    mocked_task = MagicMock()
    monkeypatch.setattr(
        "app.features.users.services.tasks.send_email_verification.send_email_verification", mocked_task
    )

    user_data = {
        "username": "newuser",
        "first_name": "New",
        "last_name": "User",
        "password": "newpassword",
        "email": "newuser@example.com",
    }
    response = test_client_fixture.post(URL, json=user_data)
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
    assert user.email is None

    mocked_task.assert_called_once()
    task_input = mocked_task.call_args[0][0]
    assert isinstance(task_input, SendEmailVerificationInput)
    assert task_input.user_id == user.id
    assert task_input.email == "newuser@example.com"


@pytest.mark.asyncio
async def test_user_cannot_register_with_existing_username(test_client_fixture: TestClient, db_fixture: AsyncSession):
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
    response = test_client_fixture.post(URL, json=user_data)
    assert response.status_code == 400
    assert response.json()["type"] == "users/common/register/username-exists"


@pytest.mark.asyncio
async def test_user_cannot_register_with_existing_email(test_client_fixture: TestClient, db_fixture: AsyncSession):
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
    response = test_client_fixture.post(URL, json=user_data)
    assert response.status_code == 400
    assert response.json()["type"] == "users/common/register/email-exists"
