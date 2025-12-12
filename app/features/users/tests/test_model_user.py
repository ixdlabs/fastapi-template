import pytest

from app.features.users.models import User
from app.features.users.tests.fixtures import UserFactory


@pytest.mark.asyncio
async def test_password_is_hashed_when_set():
    user: User = UserFactory.build()
    raw_password = "SecurePassword123!"
    user.set_password(raw_password)
    assert user.hashed_password != raw_password
    assert user.check_password(raw_password)


@pytest.mark.asyncio
async def test_check_password_returns_false_for_incorrect_password():
    user: User = UserFactory.build()
    raw_password = "SecurePassword123!"
    user.set_password(raw_password)
    assert not user.check_password("WrongPassword!")
