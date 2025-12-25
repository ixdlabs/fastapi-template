import uuid
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.testclient import TestClient
from app.config.auth import Authenticator
from app.conftest import NoOpBackground
from app.features.users.models import User, UserType
from app.features.users.tests.fixtures import UserFactory
from app.main import app

client = TestClient(app)


@pytest.mark.asyncio
async def test_user_can_update_own_profile(db_fixture: AsyncSession, authenticator_fixture: Authenticator):
    user: User = UserFactory.build(password__raw="testpassword", first_name="OldFirst", last_name="OldLast")
    db_fixture.add(user)
    await db_fixture.commit()
    await db_fixture.refresh(user)

    token, _ = authenticator_fixture.encode(user)
    update_data = {"first_name": "NewFirst", "last_name": "NewLast"}
    response = client.put(
        f"/api/v1/users/{user.id}",
        json=update_data,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "NewFirst"
    assert data["last_name"] == "NewLast"

    # Verify changes in the database
    stmt = select(User).where(User.id == user.id)
    result = await db_fixture.execute(stmt)
    updated_user = result.scalar_one()
    assert updated_user.first_name == "NewFirst"
    assert updated_user.last_name == "NewLast"


@pytest.mark.asyncio
async def test_user_cannot_update_other_user_profile(db_fixture: AsyncSession, authenticator_fixture: Authenticator):
    user1: User = UserFactory.build(password__raw="password1", first_name="First1", last_name="Last1")
    user2: User = UserFactory.build(password__raw="password2", first_name="First2", last_name="Last2")
    db_fixture.add_all([user1, user2])
    await db_fixture.commit()
    await db_fixture.refresh(user1)
    await db_fixture.refresh(user2)

    token, _ = authenticator_fixture.encode(user1)
    update_data = {"first_name": "HackedFirst", "last_name": "HackedLast"}
    response = client.put(
        f"/api/v1/users/{user2.id}",
        json=update_data,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized to update this user"

    # Verify no changes in the database
    stmt = select(User).where(User.id == user2.id)
    result = await db_fixture.execute(stmt)
    untouched_user = result.scalar_one()
    assert untouched_user.first_name == "First2"
    assert untouched_user.last_name == "Last2"


@pytest.mark.asyncio
async def test_admin_can_update_other_user_profile(db_fixture: AsyncSession, authenticator_fixture: Authenticator):
    admin_user: User = UserFactory.build(type=UserType.ADMIN, password__raw="adminpassword")
    normal_user: User = UserFactory.build(password__raw="userpassword", first_name="OldFirst", last_name="OldLast")
    db_fixture.add_all([admin_user, normal_user])
    await db_fixture.commit()
    await db_fixture.refresh(admin_user)
    await db_fixture.refresh(normal_user)

    token, _ = authenticator_fixture.encode(admin_user)
    update_data = {"first_name": "NewFirst", "last_name": "NewLast"}
    response = client.put(
        f"/api/v1/users/{normal_user.id}",
        json=update_data,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "NewFirst"
    assert data["last_name"] == "NewLast"

    # Verify changes in the database
    stmt = select(User).where(User.id == normal_user.id)
    result = await db_fixture.execute(stmt)
    updated_user = result.scalar_one()
    assert updated_user.first_name == "NewFirst"
    assert updated_user.last_name == "NewLast"


@pytest.mark.asyncio
async def test_admin_cannot_update_nonexistent_user_profile(
    db_fixture: AsyncSession, authenticator_fixture: Authenticator
):
    admin_user: User = UserFactory.build(type=UserType.ADMIN, password__raw="adminpassword")
    db_fixture.add(admin_user)
    await db_fixture.commit()
    await db_fixture.refresh(admin_user)

    token, _ = authenticator_fixture.encode(admin_user)
    update_data = {"first_name": "NewFirst", "last_name": "NewLast"}
    response = client.put(
        f"/api/v1/users/{uuid.uuid4()}",
        json=update_data,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


@pytest.mark.asyncio
async def test_user_update_email_triggers_verification(
    db_fixture: AsyncSession, authenticator_fixture: Authenticator, background_fixture: NoOpBackground
):
    user: User = UserFactory.build(password__raw="testpassword", email="test@example.com")
    db_fixture.add(user)
    await db_fixture.commit()
    await db_fixture.refresh(user)

    token, _ = authenticator_fixture.encode(user)
    update_data = {"first_name": "NewFirst", "last_name": "NewLast", "email": "newemail@example.com"}
    response = client.put(
        f"/api/v1/users/{user.id}",
        json=update_data,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "NewFirst"
    assert data["last_name"] == "NewLast"
    assert data["email"] == "test@example.com"

    assert "send_email_verification_email_task" in background_fixture.called_tasks


@pytest.mark.asyncio
async def test_user_update_email_to_existing_email_fails(
    db_fixture: AsyncSession, authenticator_fixture: Authenticator
):
    existing_user: User = UserFactory.build(email="existing@example.com")
    user: User = UserFactory.build(password__raw="testpassword", email="user@example.com")
    db_fixture.add_all([existing_user, user])
    await db_fixture.commit()
    await db_fixture.refresh(existing_user)
    await db_fixture.refresh(user)

    token, _ = authenticator_fixture.encode(user)
    update_data = {"first_name": "NewFirst", "last_name": "NewLast", "email": "existing@example.com"}
    response = client.put(
        f"/api/v1/users/{user.id}",
        json=update_data,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Email already exists"
