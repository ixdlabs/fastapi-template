import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.users.models.user import User
from app.features.users.models.user_action import UserAction, UserActionType, UserActionState
from app.fixtures.user_factory import UserFactory
from app.fixtures.user_action_factory import UserActionFactory
from fastapi.testclient import TestClient

URL = "/api/auth/verify-email"


@pytest.mark.asyncio
async def test_user_can_verify_email_confirm(test_client_fixture: TestClient, db_fixture: AsyncSession):
    user: User = UserFactory.build(email="old@example.com")
    db_fixture.add(user)
    await db_fixture.commit()
    await db_fixture.refresh(user)

    action: UserAction = UserActionFactory.build(user_id=user.id, data={"email": "new@example.com"})
    action.set_token("valid-token")
    db_fixture.add(action)
    await db_fixture.commit()
    await db_fixture.refresh(action)

    response = test_client_fixture.post(URL, json={"action_id": str(action.id), "token": "valid-token"})
    assert response.status_code == 200

    data = response.json()
    await db_fixture.refresh(user)
    assert data["user_id"] == str(user.id)
    assert data["email"] == "new@example.com"

    await db_fixture.refresh(user)
    await db_fixture.refresh(action)
    assert user.email == "new@example.com"
    assert action.state == UserActionState.COMPLETED


@pytest.mark.asyncio
async def test_user_cannot_verify_email_confirm_action_not_found(
    test_client_fixture: TestClient,
):
    response = test_client_fixture.post(URL, json={"action_id": str(uuid.uuid4()), "token": "any-token"})
    assert response.status_code == 404
    assert response.json()["type"] == "users/common/verify-email-confirm/action-not-found"


@pytest.mark.asyncio
async def test_user_cannot_verify_email_confirm_invalid_token(
    test_client_fixture: TestClient, db_fixture: AsyncSession
):
    user: User = UserFactory.build(email="old@example.com")
    db_fixture.add(user)
    await db_fixture.commit()
    await db_fixture.refresh(user)

    action: UserAction = UserActionFactory.build(user_id=user.id, data={"email": "new@example.com"})
    action.set_token("correct-token")

    db_fixture.add(action)
    await db_fixture.commit()
    await db_fixture.refresh(action)

    response = test_client_fixture.post(URL, json={"action_id": str(action.id), "token": "wrong-token"})
    assert response.status_code == 400
    assert response.json()["type"] == "users/common/verify-email-confirm/invalid-action-token"


@pytest.mark.asyncio
async def test_user_cannot_verify_email_confirm_email_already_in_use(
    test_client_fixture: TestClient, db_fixture: AsyncSession
):
    user1: User = UserFactory.build(email="user1@example.com")
    user2: User = UserFactory.build(email="user2@example.com")

    db_fixture.add_all([user1, user2])
    await db_fixture.commit()
    await db_fixture.refresh(user1)
    await db_fixture.refresh(user2)

    action: UserAction = UserActionFactory.build(user_id=user1.id, data={"email": "user2@example.com"})
    action.set_token("valid-token")
    db_fixture.add(action)
    await db_fixture.commit()
    await db_fixture.refresh(action)

    response = test_client_fixture.post(URL, json={"action_id": str(action.id), "token": "valid-token"})
    assert response.status_code == 400
    assert response.json()["type"] == "users/common/verify-email-confirm/email-already-in-use"


@pytest.mark.asyncio
async def test_user_cannot_verify_email_confirm_already_verified(
    test_client_fixture: TestClient, db_fixture: AsyncSession
):
    user: User = UserFactory.build(email="old@example.com")
    db_fixture.add(user)
    await db_fixture.commit()
    await db_fixture.refresh(user)

    action: UserAction = UserActionFactory.build(
        user_id=user.id, data={"email": "new@example.com"}, state=UserActionState.COMPLETED
    )
    action.set_token("valid-token")
    db_fixture.add(action)
    await db_fixture.commit()
    await db_fixture.refresh(action)

    response = test_client_fixture.post(URL, json={"action_id": str(action.id), "token": "valid-token"})
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_user_cannot_verify_email_confirm_action_type_mismatch(
    test_client_fixture: TestClient, db_fixture: AsyncSession
):
    user: User = UserFactory.build(email="old@example.com")
    db_fixture.add(user)
    await db_fixture.commit()
    await db_fixture.refresh(user)

    action: UserAction = UserActionFactory.build(
        user_id=user.id, data={"email": "new@example.com"}, type=UserActionType.PASSWORD_RESET
    )
    action.set_token("valid-token")
    db_fixture.add(action)
    await db_fixture.commit()
    await db_fixture.refresh(action)

    response = test_client_fixture.post(URL, json={"action_id": str(action.id), "token": "valid-token"})
    assert response.status_code == 400
    assert response.json()["type"] == "users/common/verify-email-confirm/invalid-action-token"


@pytest.mark.asyncio
async def test_user_cannot_verify_email_confirm_missing_email_in_action_data(
    test_client_fixture: TestClient, db_fixture: AsyncSession
):
    user: User = UserFactory.build(email="old@example.com")
    db_fixture.add(user)
    await db_fixture.commit()
    await db_fixture.refresh(user)

    action: UserAction = UserActionFactory.build(user_id=user.id, data={})
    action.set_token("valid-token")
    db_fixture.add(action)
    await db_fixture.commit()
    await db_fixture.refresh(action)

    response = test_client_fixture.post(URL, json={"action_id": str(action.id), "token": "valid-token"})
    assert response.status_code == 400
    assert response.json()["type"] == "users/common/verify-email-confirm/invalid-action-token"
