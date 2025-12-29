from unittest.mock import MagicMock
import pytest
from pytest import MonkeyPatch
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.testclient import TestClient
from app.features.users.models.user import User
from app.features.users.services.tasks.send_email_verification import SendEmailVerificationInput
from app.fixtures.user_factory import UserFactory

from app.main import app

client = TestClient(app)
url = "/api/v1/common/users/me"


@pytest.mark.asyncio
async def test_user_can_update_own_profile(db_fixture: AsyncSession, authenticated_user_fixture: User):
    update_data = {"first_name": "NewFirst", "last_name": "NewLast"}
    response = client.put(url, json=update_data)

    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "NewFirst"
    assert data["last_name"] == "NewLast"

    stmt = select(User).where(User.id == authenticated_user_fixture.id)
    result = await db_fixture.execute(stmt)
    updated_user = result.scalar_one()
    assert updated_user.first_name == "NewFirst"
    assert updated_user.last_name == "NewLast"


@pytest.mark.asyncio
async def test_user_can_update_email_triggers_verification(authenticated_user_fixture: User, monkeypatch: MonkeyPatch):
    mocked_task = MagicMock()
    monkeypatch.setattr(
        "app.features.users.services.tasks.send_email_verification.send_email_verification", mocked_task
    )

    update_data = {"first_name": "NewFirst", "last_name": "NewLast", "email": "newemail@example.com"}
    response = client.put(url, json=update_data)
    assert response.status_code == 200

    data = response.json()
    assert data["first_name"] == "NewFirst"
    assert data["last_name"] == "NewLast"
    assert data["email"] == authenticated_user_fixture.email  # Email not updated yet

    mocked_task.assert_called_once()
    task_input = mocked_task.call_args[0][0]
    assert isinstance(task_input, SendEmailVerificationInput)
    assert task_input.user_id == authenticated_user_fixture.id
    assert task_input.email == "newemail@example.com"


@pytest.mark.asyncio
async def test_user_cannot_update_email_to_existing_email(db_fixture: AsyncSession, authenticated_user_fixture: User):
    assert authenticated_user_fixture is not None

    existing_user: User = UserFactory.build(email="existing@example.com")
    db_fixture.add(existing_user)
    await db_fixture.commit()
    await db_fixture.refresh(existing_user)
    await db_fixture.refresh(authenticated_user_fixture)

    update_data = {"first_name": "NewFirst", "last_name": "NewLast", "email": "existing@example.com"}
    response = client.put(url, json=update_data)
    assert response.status_code == 400
    assert response.json()["type"] == "users/common/update/email-exists"
