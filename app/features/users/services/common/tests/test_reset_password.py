import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.conftest import NoOpTaskTrackingBackground
from app.features.users.models.user import User
from app.features.users.services.tasks.send_password_reset_email import SendPasswordResetInput
from app.fixtures.user_factory import UserFactory
from app.main import app

client = TestClient(app)
url = "/api/auth/reset-password"


@pytest.mark.asyncio
async def test_user_can_reset_password(db_fixture: AsyncSession, background_fixture: NoOpTaskTrackingBackground):
    user: User = UserFactory.build(email="user@example.com")
    db_fixture.add(user)
    await db_fixture.commit()
    await db_fixture.refresh(user)

    payload = {"email": "user@example.com"}
    response = client.post(url, json=payload)
    assert response.status_code == 200

    assert response.json() == {"detail": "If the email exists, a password reset link has been sent."}
    assert "send_password_reset_email_task" in background_fixture.called_tasks

    task_args, _ = background_fixture.called_tasks["send_password_reset_email_task"][0]
    assert isinstance(task_args[0], str)
    task_input = SendPasswordResetInput.model_validate_json(task_args[0])
    assert task_input.user_id == user.id
    assert task_input.email == user.email


@pytest.mark.asyncio
async def test_user_cannot_reset_password_with_nonexistent_email(background_fixture: NoOpTaskTrackingBackground):
    payload = {"email": "doesnotexist@example.com"}
    response = client.post(url, json=payload)
    assert response.status_code == 200

    assert response.json()["detail"] == "If the email exists, a password reset link has been sent."
    assert background_fixture.called_tasks == {}
