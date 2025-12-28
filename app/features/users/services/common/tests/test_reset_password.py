import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from unittest.mock import MagicMock

from app.features.users.models.user import User
from app.features.users.services.tasks.send_password_reset_email import SendPasswordResetInput
from app.fixtures.user_factory import UserFactory
from app.main import app

client = TestClient(app)
url = "/api/auth/reset-password"


@pytest.mark.asyncio
async def test_user_can_reset_password(db_fixture: AsyncSession, celery_background_fixture: MagicMock):
    user: User = UserFactory.build(email="user@example.com")
    db_fixture.add(user)
    await db_fixture.commit()
    await db_fixture.refresh(user)

    payload = {"email": "user@example.com"}
    response = client.post(url, json=payload)
    assert response.status_code == 200

    assert response.json() == {"detail": "If the email exists, a password reset link has been sent."}

    # Background task was submitted
    celery_background_fixture.apply_async.assert_called_once()
    _, kwargs = celery_background_fixture.apply_async.call_args
    assert isinstance(kwargs["args"][0], str)
    task_input = SendPasswordResetInput.model_validate_json(kwargs["args"][0])
    assert task_input.user_id == user.id
    assert task_input.email == user.email


@pytest.mark.asyncio
async def test_user_cannot_reset_password_with_nonexistent_email(celery_background_fixture: MagicMock):
    payload = {"email": "doesnotexist@example.com"}
    response = client.post(url, json=payload)
    assert response.status_code == 200

    assert response.json()["detail"] == "If the email exists, a password reset link has been sent."
    celery_background_fixture.apply_async.assert_not_called()
