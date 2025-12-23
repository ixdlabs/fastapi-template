from datetime import datetime, timedelta
import pytest

from app.features.users.models import UserEmailVerification, UserEmailVerificationState
from app.features.users.tests.fixtures import UserEmailVerificationFactory


@pytest.mark.asyncio
async def test_verification_token_is_hashed_when_set():
    user: UserEmailVerification = UserEmailVerificationFactory.build()
    raw_token = "SecurePassword123!"
    user.set_verification_token(raw_token)
    assert user.hashed_verification_token != raw_token
    assert user.is_valid(raw_token)


@pytest.mark.asyncio
async def test_is_valid_returns_false_for_incorrect_verification_token():
    user: UserEmailVerification = UserEmailVerificationFactory.build()
    raw_token = "SecurePassword123!"
    user.set_verification_token(raw_token)
    assert not user.is_valid("WrongToken!")


@pytest.mark.asyncio
async def test_is_valid_returns_false_for_expired_token():
    user: UserEmailVerification = UserEmailVerificationFactory.build(expires_at=datetime.now() - timedelta(minutes=1))
    raw_token = "SecurePassword123!"
    user.set_verification_token(raw_token)
    assert not user.is_valid(raw_token)


@pytest.mark.asyncio
async def test_is_valid_returns_false_for_non_pending_state():
    user: UserEmailVerification = UserEmailVerificationFactory.build(state=UserEmailVerificationState.VERIFIED)
    raw_token = "SecurePassword123!"
    user.set_verification_token(raw_token)
    assert not user.is_valid(raw_token)
