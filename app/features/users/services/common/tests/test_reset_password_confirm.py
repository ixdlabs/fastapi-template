import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.testclient import TestClient

from app.features.users.models.user import User
from app.features.users.models.user_action import UserAction, UserActionType, UserActionState
from app.fixtures.user_factory import UserFactory
from app.fixtures.user_action_factory import UserActionFactory

URL = "/api/auth/reset-password-confirm"


@pytest.mark.asyncio
async def test_user_can_reset_password(test_client_fixture: TestClient, db_fixture: AsyncSession):
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

    payload = {"action_id": str(action.id), "token": "valid-token", "new_password": "new-secure-password"}
    response = test_client_fixture.post(URL, json=payload)
    assert response.status_code == 200

    await db_fixture.refresh(user)
    await db_fixture.refresh(action)
    assert user.hashed_password != old_password_hash
    assert action.state == UserActionState.COMPLETED


@pytest.mark.asyncio
async def test_user_cannot_reset_password_with_invalid_action_id(
    test_client_fixture: TestClient,
):
    payload = {"action_id": str(uuid.uuid4()), "token": "any-token", "new_password": "password"}
    response = test_client_fixture.post(URL, json=payload)

    assert response.status_code == 404
    assert response.json()["type"] == "users/common/reset-password-confirm/action-not-found"


@pytest.mark.asyncio
async def test_user_cannot_reset_password_with_different_action_type(
    test_client_fixture: TestClient, db_fixture: AsyncSession
):
    user: User = UserFactory.build()
    db_fixture.add(user)
    await db_fixture.commit()
    await db_fixture.refresh(user)

    action: UserAction = UserActionFactory.build(user_id=user.id, type=UserActionType.EMAIL_VERIFICATION)
    action.set_token("some-token")
    db_fixture.add(action)
    await db_fixture.commit()
    await db_fixture.refresh(action)

    payload = {"action_id": str(action.id), "token": "some-token", "new_password": "password"}
    response = test_client_fixture.post(URL, json=payload)

    assert response.status_code == 400
    assert response.json()["type"] == "users/common/reset-password-confirm/invalid-action-token"


@pytest.mark.asyncio
async def test_user_cannot_reset_password_with_invalid_token(test_client_fixture: TestClient, db_fixture: AsyncSession):
    user: User = UserFactory.build()
    db_fixture.add(user)
    await db_fixture.commit()
    await db_fixture.refresh(user)

    action: UserAction = UserActionFactory.build(user_id=user.id, type=UserActionType.PASSWORD_RESET)
    action.set_token("correct-token")
    db_fixture.add(action)
    await db_fixture.commit()
    await db_fixture.refresh(action)

    payload = {"action_id": str(action.id), "token": "wrong-token", "new_password": "password"}
    response = test_client_fixture.post(URL, json=payload)

    assert response.status_code == 400
    assert response.json()["type"] == "users/common/reset-password-confirm/invalid-action-token"


@pytest.mark.asyncio
async def test_user_cannot_reset_password_with_already_completed_action(
    test_client_fixture: TestClient, db_fixture: AsyncSession
):
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

    payload = {"action_id": str(action.id), "token": "wrong-token", "new_password": "password"}
    response = test_client_fixture.post(URL, json=payload)
    assert response.status_code == 400
    assert response.json()["type"] == "users/common/reset-password-confirm/invalid-action-token"
