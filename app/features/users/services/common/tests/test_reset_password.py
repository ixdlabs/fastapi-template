from fastapi import FastAPI
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from unittest.mock import AsyncMock

from app.features.users.models.user import User
from app.features.users.services.tasks.send_password_reset_email import (
    SendPasswordResetInput,
    send_password_reset_email,
)
from app.fixtures.user_factory import UserFactory

URL = "/api/auth/reset-password"


@pytest.mark.asyncio
async def test_user_can_reset_password(
    test_client_fixture: TestClient, db_fixture: AsyncSession, fastapi_app_fixture: FastAPI
):
    user: User = UserFactory.build(email="user@example.com")
    db_fixture.add(user)
    await db_fixture.commit()
    await db_fixture.refresh(user)

    mocked_task = AsyncMock()
    fastapi_app_fixture.dependency_overrides[send_password_reset_email] = lambda: mocked_task

    payload = {"email": "user@example.com"}
    response = test_client_fixture.post(URL, json=payload)
    assert response.status_code == 200

    mocked_task.submit.assert_called_once()
    task_input = mocked_task.submit.call_args[0][0]
    assert isinstance(task_input, SendPasswordResetInput)
    assert task_input.user_id == user.id
    assert task_input.email == "user@example.com"


@pytest.mark.asyncio
async def test_user_cannot_reset_password_with_nonexistent_email(
    test_client_fixture: TestClient, fastapi_app_fixture: FastAPI
):
    mocked_task = AsyncMock()
    fastapi_app_fixture.dependency_overrides[send_password_reset_email] = lambda: mocked_task

    payload = {"email": "doesnotexist@example.com"}
    response = test_client_fixture.post(URL, json=payload)
    assert response.status_code == 200

    mocked_task.submit.assert_not_called()
