import uuid
import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.auth import TaskRunner
from app.config.settings import Settings
from app.features.users.models.user_action import UserAction, UserActionState, UserActionType
from app.features.users.services.tasks.send_password_reset_email import (
    SendPasswordResetInput,
    send_password_reset_email,
)


def fake_settings():
    return Settings.model_construct(password_reset_expiration_minutes=45)


# ----------------------------------------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_password_reset_email_creates_action_and_invalidates_previous(
    db_fixture: AsyncSession, task_runner_fixture: TaskRunner
):
    user_id = uuid.uuid4()
    email = "reset@example.com"

    # Existing pending password reset action
    old_action = UserAction(
        type=UserActionType.PASSWORD_RESET,
        user_id=user_id,
        state=UserActionState.PENDING,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )
    old_action.set_token("old-reset-token")

    db_fixture.add(old_action)
    await db_fixture.commit()
    await db_fixture.refresh(old_action)

    task_input = SendPasswordResetInput(user_id=user_id, email=email)
    before_call = datetime.now(timezone.utc)

    await send_password_reset_email(
        task_input=task_input, task_runner=task_runner_fixture, settings=fake_settings(), db=db_fixture
    )

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
    assert new_action.type == UserActionType.PASSWORD_RESET
    assert new_action.state == UserActionState.PENDING
    assert new_action.expires_at is not None
    assert new_action.hashed_token is not None

    # Expiration window correctness
    assert before_call + timedelta(minutes=45) <= new_action.expires_at <= after_call + timedelta(minutes=45)
