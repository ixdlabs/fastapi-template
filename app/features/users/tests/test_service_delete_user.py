import uuid
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.testclient import TestClient
from app.config.auth import Authenticator
from app.features.users.models import User, UserType
from app.features.users.tests.fixtures import UserFactory
from app.main import app

client = TestClient(app)


@pytest.mark.asyncio
async def test_user_can_delete_own_account(db_fixture: AsyncSession, authenticator_fixture: Authenticator):
    user: User = UserFactory.build(password__raw="testpassword")
    db_fixture.add(user)
    await db_fixture.commit()
    await db_fixture.refresh(user)

    token, _ = authenticator_fixture.encode(user)
    response = client.delete(f"/api/v1/users/{user.id}", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 204

    # Verify user is deleted
    stmt = select(User).where(User.id == user.id)
    result = await db_fixture.execute(stmt)
    deleted_user = result.scalar_one_or_none()
    assert deleted_user is None


@pytest.mark.asyncio
async def test_user_cannot_delete_other_user_account(db_fixture: AsyncSession, authenticator_fixture: Authenticator):
    user1: User = UserFactory.build(password__raw="password1")
    user2: User = UserFactory.build(password__raw="password2")
    db_fixture.add_all([user1, user2])
    await db_fixture.commit()
    await db_fixture.refresh(user1)
    await db_fixture.refresh(user2)

    token, _ = authenticator_fixture.encode(user1)
    response = client.delete(f"/api/v1/users/{user2.id}", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized to delete this user"


@pytest.mark.asyncio
async def test_admin_can_delete_other_user_account(db_fixture: AsyncSession, authenticator_fixture: Authenticator):
    admin_user: User = UserFactory.build(type=UserType.ADMIN, password__raw="adminpassword")
    normal_user: User = UserFactory.build(password__raw="userpassword")
    db_fixture.add_all([admin_user, normal_user])
    await db_fixture.commit()
    await db_fixture.refresh(admin_user)
    await db_fixture.refresh(normal_user)

    token, _ = authenticator_fixture.encode(admin_user)
    response = client.delete(f"/api/v1/users/{normal_user.id}", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 204

    # Verify user is deleted
    stmt = select(User).where(User.id == normal_user.id)
    result = await db_fixture.execute(stmt)
    deleted_user = result.scalar_one_or_none()
    assert deleted_user is None


@pytest.mark.asyncio
async def test_admin_cannot_delete_nonexistent_user(db_fixture: AsyncSession, authenticator_fixture: Authenticator):
    admin_user: User = UserFactory.build(type=UserType.ADMIN, password__raw="adminpassword")
    db_fixture.add(admin_user)
    await db_fixture.commit()
    await db_fixture.refresh(admin_user)

    token, _ = authenticator_fixture.encode(admin_user)
    response = client.delete(f"/api/v1/users/{uuid.uuid4()}", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"
