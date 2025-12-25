from unittest.mock import AsyncMock
import uuid
import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings
from app.features.users.models import UserAction, UserActionState, UserActionType
from app.features.users.tasks.email_verification import (
    SendEmailVerificationInput,
    send_email_verification_email,
    send_email_verification_email_task,
)


def fake_settings():
    return Settings.model_construct(email_verification_expiration_minutes=30)


@pytest.mark.asyncio
async def test_send_email_verification_email_creates_action_and_invalidates_previous(db_fixture: AsyncSession):
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

    task_input = SendEmailVerificationInput(user_id=user_id, email=email)
    before_call = datetime.now(timezone.utc)

    await send_email_verification_email(task_input=task_input, settings=fake_settings(), db=db_fixture)
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
async def test_send_email_verification_email_task_calls_function(monkeypatch: pytest.MonkeyPatch):
    user_id = uuid.uuid4()
    email = "test@example.com"

    task_input = SendEmailVerificationInput(user_id=user_id, email=email)
    raw_task_input = task_input.model_dump_json()

    mocked_function = AsyncMock()
    monkeypatch.setattr("app.config.database.get_db", AsyncMock())
    monkeypatch.setattr("app.features.users.tasks.email_verification.send_email_verification_email", mocked_function)

    send_email_verification_email_task(raw_task_input)
    mocked_function.assert_awaited_once()
    args, kwargs = mocked_function.call_args
    called_task_input = kwargs.get("task_input") or args[0]
    assert called_task_input.user_id == user_id
    assert called_task_input.email == email
