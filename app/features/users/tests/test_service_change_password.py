import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.users.models import User
from app.features.users.tests.fixtures import UserFactory
from app.config.auth import Authenticator
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.mark.asyncio
async def test_change_password_success(db_fixture: AsyncSession, authenticator_fixture: Authenticator):
    user: User = UserFactory.build()
    user.set_password("old-password")
    db_fixture.add(user)
    await db_fixture.commit()
    await db_fixture.refresh(user)

    token, _ = authenticator_fixture.encode(user)
    response = client.post(
        "/api/auth/change-password",
        json={"old_password": "old-password", "new_password": "new-password"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["detail"] == "Password change successful."

    await db_fixture.refresh(user)
    assert user.check_password("new-password")


@pytest.mark.asyncio
async def test_change_password_incorrect_old_password(db_fixture: AsyncSession, authenticator_fixture: Authenticator):
    user: User = UserFactory.build()
    user.set_password("old-password")
    db_fixture.add(user)
    await db_fixture.commit()
    await db_fixture.refresh(user)

    token, _ = authenticator_fixture.encode(user)
    response = client.post(
        "/api/auth/change-password",
        json={"old_password": "wrong-old-password", "new_password": "new-password"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Old password is incorrect"


@pytest.mark.asyncio
async def test_change_password_same_as_old(db_fixture: AsyncSession, authenticator_fixture: Authenticator):
    user: User = UserFactory.build()
    user.set_password("old-password")
    db_fixture.add(user)
    await db_fixture.commit()
    await db_fixture.refresh(user)

    token, _ = authenticator_fixture.encode(user)
    response = client.post(
        "/api/auth/change-password",
        json={"old_password": "old-password", "new_password": "old-password"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "New password must be different from old password"


@pytest.mark.asyncio
async def test_change_password_user_not_found(db_fixture: AsyncSession, authenticator_fixture: Authenticator):
    user: User = UserFactory.build()
    user.set_password("old-password")
    db_fixture.add(user)
    await db_fixture.commit()
    await db_fixture.refresh(user)

    token, _ = authenticator_fixture.encode(user)
    # Delete the user to simulate not found
    await db_fixture.delete(user)
    await db_fixture.commit()

    response = client.post(
        "/api/auth/change-password",
        json={"old_password": "old-password", "new_password": "new-password"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


@pytest.mark.asyncio
async def test_change_password_unauthorized():
    response = client.post(
        "/api/auth/change-password",
        json={"old_password": "old-password", "new_password": "new-password"},
    )
    assert response.status_code == 401
