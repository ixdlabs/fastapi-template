import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.users.models.user import User
from app.fixtures.user_factory import UserFactory
from app.config.auth import Authenticator
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
url = "/api/auth/change-password"


@pytest.mark.asyncio
async def test_user_can_change_password(db_fixture: AsyncSession, authenticator_fixture: Authenticator):
    user: User = UserFactory.build()
    user.set_password("old-password")
    db_fixture.add(user)
    await db_fixture.commit()
    await db_fixture.refresh(user)
    token, _ = authenticator_fixture.encode(user)

    payload = {"old_password": "old-password", "new_password": "new-password"}
    response = client.post(url, json=payload, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200

    data = response.json()
    assert data["detail"] == "Password change successful."
    await db_fixture.refresh(user)
    assert user.check_password("new-password")


@pytest.mark.asyncio
async def test_user_cannot_change_password_with_incorrect_old_password(
    db_fixture: AsyncSession, authenticator_fixture: Authenticator
):
    user: User = UserFactory.build()
    user.set_password("old-password")
    db_fixture.add(user)
    await db_fixture.commit()
    await db_fixture.refresh(user)
    token, _ = authenticator_fixture.encode(user)

    payload = {"old_password": "wrong-old-password", "new_password": "new-password"}
    response = client.post(url, json=payload, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 400
    assert response.json()["type"] == "users/common/change-password/password-incorrect"


@pytest.mark.asyncio
async def test_user_cannot_change_password_with_same_old_password(
    db_fixture: AsyncSession, authenticator_fixture: Authenticator
):
    user: User = UserFactory.build()
    user.set_password("old-password")
    db_fixture.add(user)
    await db_fixture.commit()
    await db_fixture.refresh(user)

    token, _ = authenticator_fixture.encode(user)
    payload = {"old_password": "old-password", "new_password": "old-password"}
    response = client.post(url, json=payload, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 400
    assert response.json()["type"] == "users/common/change-password/passwords-identical"


@pytest.mark.asyncio
async def test_user_cannot_change_password_if_account_deleted(
    db_fixture: AsyncSession, authenticator_fixture: Authenticator
):
    user: User = UserFactory.build()
    user.set_password("old-password")
    db_fixture.add(user)
    await db_fixture.commit()
    await db_fixture.refresh(user)
    token, _ = authenticator_fixture.encode(user)
    # Delete the user to simulate not found
    await db_fixture.delete(user)
    await db_fixture.commit()

    payload = {"old_password": "old-password", "new_password": "new-password"}
    response = client.post(url, json=payload, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 404
    assert response.json()["type"] == "users/common/change-password/user-not-found"


@pytest.mark.asyncio
async def test_unauthorized_user_cannot_change_password():
    response = client.post(url, json={"old_password": "old-password", "new_password": "new-password"})
    assert response.status_code == 401
