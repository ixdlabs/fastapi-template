from datetime import datetime, timedelta, timezone
import pytest

from app.features.users.models import UserAction, UserActionState
from app.features.users.tests.fixtures import UserActionFactory


@pytest.mark.asyncio
async def test_token_is_hashed_when_set():
    user: UserAction = UserActionFactory.build()
    raw_token = "SecurePassword123!"
    user.set_token(raw_token)
    assert user.hashed_token != raw_token
    assert user.is_valid(raw_token)


@pytest.mark.asyncio
async def test_is_valid_returns_false_for_incorrect_token():
    user: UserAction = UserActionFactory.build()
    raw_token = "SecurePassword123!"
    user.set_token(raw_token)
    assert not user.is_valid("WrongToken!")


@pytest.mark.asyncio
async def test_is_valid_returns_false_for_expired_token():
    old_expiration_time = datetime.now(timezone.utc) - timedelta(minutes=1)
    user: UserAction = UserActionFactory.build(expires_at=old_expiration_time)
    raw_token = "SecurePassword123!"
    user.set_token(raw_token)
    assert not user.is_valid(raw_token)


@pytest.mark.asyncio
async def test_is_valid_returns_false_for_non_pending_state():
    user: UserAction = UserActionFactory.build(state=UserActionState.COMPLETED)
    raw_token = "SecurePassword123!"
    user.set_token(raw_token)
    assert not user.is_valid(raw_token)
