import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.conftest import NoOpBackground
from app.features.users.models import User
from app.features.users.services.send_password_reset_email import SendPasswordResetInput
from app.features.users.tests.fixtures import UserFactory
from app.main import app

client = TestClient(app)


@pytest.mark.asyncio
async def test_reset_password_with_existing_email_sends_task(
    db_fixture: AsyncSession, background_fixture: NoOpBackground
):
    user: User = UserFactory.build(email="user@example.com")
    db_fixture.add(user)
    await db_fixture.commit()
    await db_fixture.refresh(user)

    payload = {"email": "user@example.com"}
    response = client.post("/api/auth/reset-password", json=payload)
    assert response.status_code == 200
    assert response.json() == {"detail": "If the email exists, a password reset link has been sent."}
    assert "send_password_reset_email_task" in background_fixture.called_tasks

    task_args, _ = background_fixture.called_tasks["send_password_reset_email_task"][0]
    task_input = SendPasswordResetInput.model_validate_json(task_args[0])
    assert task_input.user_id == user.id
    assert task_input.email == user.email


@pytest.mark.asyncio
async def test_reset_password_with_nonexistent_email_is_silent(background_fixture: NoOpBackground):
    payload = {"email": "doesnotexist@example.com"}
    response = client.post("/api/auth/reset-password", json=payload)
    assert response.status_code == 200
    assert response.json()["detail"] == "If the email exists, a password reset link has been sent."
    assert background_fixture.called_tasks == {}
