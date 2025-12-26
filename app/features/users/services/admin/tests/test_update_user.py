import uuid
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.testclient import TestClient
from app.features.users.models.user import UserType, User
from app.fixtures.user_factory import UserFactory
from app.main import app

client = TestClient(app)
base_url = "/api/v1/admin/users"


@pytest.mark.asyncio
async def test_admin_can_update_other_user_profile(db_fixture: AsyncSession, authenticated_admin_fixture: User):
    assert authenticated_admin_fixture.type == UserType.ADMIN

    user1: User = UserFactory.build(password__raw="userpassword", first_name="OldFirst", last_name="OldLast")
    db_fixture.add_all([user1])
    await db_fixture.commit()
    await db_fixture.refresh(user1)

    payload = {"first_name": "NewFirst", "last_name": "NewLast"}
    response = client.put(f"{base_url}/{user1.id}", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["first_name"] == "NewFirst"
    assert data["last_name"] == "NewLast"

    stmt = select(User).where(User.id == user1.id)
    result = await db_fixture.execute(stmt)
    updated_user = result.scalar_one()
    assert updated_user.first_name == "NewFirst"
    assert updated_user.last_name == "NewLast"


@pytest.mark.asyncio
async def test_admin_cannot_update_nonexistent_user_profile(authenticated_admin_fixture: User):
    assert authenticated_admin_fixture.type == UserType.ADMIN

    payload = {"first_name": "NewFirst", "last_name": "NewLast"}
    response = client.put(f"{base_url}/{uuid.uuid4()}", json=payload)
    assert response.status_code == 404
    assert response.json()["type"] == "users/admin/update/user-not-found"


@pytest.mark.asyncio
async def test_admin_cannot_update_user_email_to_existing_email(
    db_fixture: AsyncSession, authenticated_admin_fixture: User
):
    assert authenticated_admin_fixture.type == UserType.ADMIN

    user1: User = UserFactory.build(password__raw="userpassword", email="user1@example.com")
    user2: User = UserFactory.build(password__raw="userpassword", email="user2@example.com")
    db_fixture.add_all([user1, user2])
    await db_fixture.commit()
    await db_fixture.refresh(user1)
    await db_fixture.refresh(user2)

    payload = {"first_name": "NewFirst", "last_name": "NewLast", "email": "user2@example.com"}
    response = client.put(f"{base_url}/{user1.id}", json=payload)
    assert response.status_code == 400
    assert response.json()["type"] == "users/admin/update/email-exists"
