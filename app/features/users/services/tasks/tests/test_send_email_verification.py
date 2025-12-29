from unittest.mock import MagicMock
import uuid
import pytest
from datetime import datetime, timezone, timedelta
from pytest import MonkeyPatch
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthUser
from app.features.users.models.user_action import UserAction, UserActionState, UserActionType
from fastapi.testclient import TestClient

from app.features.users.services.tasks.send_email_verification import SendEmailVerificationInput, run_task_in_worker
from app.main import app

client = TestClient(app)
url = "/api/v1/tasks/users/send-email-verification"

# ----------------------------------------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_email_verification_creates_action_and_invalidates_previous(
    db_fixture: AsyncSession, authenticated_admin_fixture: AuthUser
):
    user_id = uuid.uuid4()
    email = "new@example.com"

    # Existing pending verification action
    old_action = UserAction(
        type=UserActionType.EMAIL_VERIFICATION,
        user_id=user_id,
        data={"email": "old@example.com"},
        state=UserActionState.PENDING,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )
    old_action.set_token("old-token")

    db_fixture.add(old_action)
    await db_fixture.commit()
    await db_fixture.refresh(old_action)

    before_call = datetime.now(timezone.utc)
    payload = {"user_id": str(user_id), "email": email}
    response = client.post(url, json=payload)
    assert response.status_code == 200
    after_call = datetime.now(timezone.utc)

    # Reload all actions for user
    result = await db_fixture.execute(select(UserAction).where(UserAction.user_id == user_id))
    actions = result.scalars().all()
    assert len(actions) == 2

    # Old action invalidated
    obsolete_action = next(a for a in actions if a.id == old_action.id)
    assert obsolete_action.state == UserActionState.OBSOLETE

    # New action assertions
    new_action = next(a for a in actions if a.id != old_action.id)
    assert new_action.type == UserActionType.EMAIL_VERIFICATION
    assert new_action.state == UserActionState.PENDING
    assert new_action.data == {"email": email}
    assert new_action.expires_at is not None
    assert new_action.hashed_token is not None

    # Expiration window correctness
    assert before_call + timedelta(minutes=30) <= new_action.expires_at <= after_call + timedelta(minutes=30)


@pytest.mark.asyncio
async def test_send_email_verification_task_executed_as_task(monkeypatch: MonkeyPatch):
    mocked_task = MagicMock()
    monkeypatch.setattr(
        "app.features.users.services.tasks.send_email_verification.send_email_verification", mocked_task
    )

    user_id = uuid.uuid4()
    background_task = run_task_in_worker()
    await background_task.submit(SendEmailVerificationInput(user_id=user_id, email="new@example.com"))

    mocked_task.assert_called_once()
    task_input = mocked_task.call_args[0][0]
    assert isinstance(task_input, SendEmailVerificationInput)
    assert task_input.user_id == user_id
    assert task_input.email == "new@example.com"
