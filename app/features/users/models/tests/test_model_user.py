import pytest

from app.features.users.models.user import User, UserType
from app.fixtures.user_factory import UserFactory


@pytest.mark.asyncio
async def test_password_is_hashed_when_set():
    user: User = UserFactory.build()
    password_set_at_prev = user.password_set_at
    raw_password = "SecurePassword123!"
    user.set_password(raw_password)
    assert user.hashed_password != raw_password
    assert user.password_set_at > password_set_at_prev
    assert user.check_password(raw_password)


@pytest.mark.asyncio
async def test_check_password_returns_false_for_incorrect_password():
    user: User = UserFactory.build()
    raw_password = "SecurePassword123!"
    user.set_password(raw_password)
    assert not user.check_password("WrongPassword!")


def test_oauth2_scopes_are_set_correctly():
    user: User = UserFactory.build(type=UserType.ADMIN)
    assert user.get_oauth2_scopes() == {"admin", "user"}


def test_oauth2_scopes_for_customer():
    user: User = UserFactory.build(type=UserType.CUSTOMER)
    assert user.get_oauth2_scopes() == {"customer", "user"}


def test_oauth2_scopes_for_unknown_type():
    user: User = UserFactory.build(type=None)
    assert user.get_oauth2_scopes() == {"user"}
