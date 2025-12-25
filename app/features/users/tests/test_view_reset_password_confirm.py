import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.testclient import TestClient

from app.main import app
from app.features.users.models import User, UserAction, UserActionState, UserActionType
from app.features.users.tests.fixtures import UserFactory, UserActionFactory

client = TestClient(app)


@pytest.mark.asyncio
async def test_reset_password_confirm_success(db_fixture: AsyncSession):
    user: User = UserFactory.build()
    db_fixture.add(user)
    await db_fixture.commit()
    await db_fixture.refresh(user)

    old_password_hash = user.hashed_password
    action: UserAction = UserActionFactory.build(user_id=user.id, type=UserActionType.PASSWORD_RESET)
    action.set_token("valid-token")

    db_fixture.add(action)
    await db_fixture.commit()
    await db_fixture.refresh(action)

    response = client.post(
        "/api/auth/reset-password-confirm",
        json={"action_id": str(action.id), "token": "valid-token", "new_password": "new-secure-password"},
    )

    assert response.status_code == 200
    await db_fixture.refresh(user)
    await db_fixture.refresh(action)

    assert user.hashed_password != old_password_hash
    assert action.state == UserActionState.COMPLETED


@pytest.mark.asyncio
async def test_reset_password_confirm_action_not_found():
    response = client.post(
        "/api/auth/reset-password-confirm",
        json={"action_id": str(uuid.uuid4()), "token": "any-token", "new_password": "password"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Action not found"


@pytest.mark.asyncio
async def test_reset_password_confirm_different_action_type(db_fixture: AsyncSession):
    user: User = UserFactory.build()
    db_fixture.add(user)
    await db_fixture.commit()
    await db_fixture.refresh(user)

    action: UserAction = UserActionFactory.build(user_id=user.id, type=UserActionType.EMAIL_VERIFICATION)
    action.set_token("some-token")

    db_fixture.add(action)
    await db_fixture.commit()
    await db_fixture.refresh(action)

    response = client.post(
        "/api/auth/reset-password-confirm",
        json={"action_id": str(action.id), "token": "some-token", "new_password": "password"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid action type"


@pytest.mark.asyncio
async def test_reset_password_confirm_invalid_token(db_fixture: AsyncSession):
    user: User = UserFactory.build()
    db_fixture.add(user)
    await db_fixture.commit()
    await db_fixture.refresh(user)

    action: UserAction = UserActionFactory.build(user_id=user.id, type=UserActionType.PASSWORD_RESET)
    action.set_token("correct-token")

    db_fixture.add(action)
    await db_fixture.commit()
    await db_fixture.refresh(action)

    response = client.post(
        "/api/auth/reset-password-confirm",
        json={"action_id": str(action.id), "token": "wrong-token", "new_password": "password"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid action token"


@pytest.mark.asyncio
async def test_reset_password_confirm_user_not_found(db_fixture: AsyncSession):
    action: UserAction = UserActionFactory.build(user_id=uuid.uuid4(), type=UserActionType.PASSWORD_RESET)
    action.set_token("valid-token")

    db_fixture.add(action)
    await db_fixture.commit()
    await db_fixture.refresh(action)

    response = client.post(
        "/api/auth/reset-password-confirm",
        json={"action_id": str(action.id), "token": "valid-token", "new_password": "password"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


@pytest.mark.asyncio
async def test_reset_password_confirm_already_completed(db_fixture: AsyncSession):
    user: User = UserFactory.build()
    db_fixture.add(user)
    await db_fixture.commit()
    await db_fixture.refresh(user)

    action: UserAction = UserActionFactory.build(
        user_id=user.id, state=UserActionState.COMPLETED, type=UserActionType.PASSWORD_RESET
    )
    action.set_token("valid-token")

    db_fixture.add(action)
    await db_fixture.commit()
    await db_fixture.refresh(action)

    response = client.post(
        "/api/auth/reset-password-confirm",
        json={"action_id": str(action.id), "token": "valid-token", "new_password": "password"},
    )

    assert response.status_code == 400
