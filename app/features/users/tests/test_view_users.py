import uuid
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.testclient import TestClient
from app.config.settings import Settings
from app.features.users.helpers import jwt_encode
from app.features.users.models import User
from app.features.users.tests.fixtures import UserFactory
from app.main import app

client = TestClient(app)


@pytest.mark.asyncio
async def test_logged_in_user_can_access_me_endpoint(db_fixture: AsyncSession, settings_fixture: Settings):
    user: User = UserFactory.build(password__raw="testpassword")
    db_fixture.add(user)
    await db_fixture.commit()
    await db_fixture.refresh(user)

    token = jwt_encode(user, settings_fixture)
    response = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(user.id)
    assert data["username"] == user.username


@pytest.mark.asyncio
async def test_user_cannot_access_other_user_detail(db_fixture: AsyncSession, settings_fixture: Settings):
    user1: User = UserFactory.build(password__raw="password1")
    user2: User = UserFactory.build(password__raw="password2")
    db_fixture.add_all([user1, user2])
    await db_fixture.commit()
    await db_fixture.refresh(user1)
    await db_fixture.refresh(user2)

    token = jwt_encode(user1, settings_fixture)
    response = client.get(f"/api/v1/users/{user2.id}", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403
    assert response.json() == {"detail": "Not authorized to access this user"}


@pytest.mark.asyncio
async def test_user_can_access_own_detail(db_fixture: AsyncSession, settings_fixture: Settings):
    user: User = UserFactory.build(password__raw="testpassword")
    db_fixture.add(user)
    await db_fixture.commit()
    await db_fixture.refresh(user)

    token = jwt_encode(user, settings_fixture)
    response = client.get(f"/api/v1/users/{user.id}", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(user.id)
    assert data["username"] == user.username


@pytest.mark.asyncio
async def test_user_can_not_access_nonexistent_user(db_fixture: AsyncSession, settings_fixture: Settings):
    user: User = UserFactory.build(password__raw="testpassword")
    db_fixture.add(user)
    await db_fixture.commit()
    await db_fixture.refresh(user)

    token = jwt_encode(user, settings_fixture)
    response = client.get(f"/api/v1/users/{uuid.uuid4()}", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403
    assert response.json() == {"detail": "Not authorized to access this user"}


@pytest.mark.asyncio
async def test_user_list_pagination_and_search(db_fixture: AsyncSession, settings_fixture: Settings):
    users = [
        UserFactory.build(username="alice", first_name="Alice", last_name="Anderson", password__raw="password1"),
        UserFactory.build(username="bob", first_name="Bob", last_name="Brown", password__raw="password2"),
        UserFactory.build(username="charlie", first_name="Charlie", last_name="Clark", password__raw="password3"),
    ]
    db_fixture.add_all(users)
    await db_fixture.commit()
    for user in users:
        await db_fixture.refresh(user)

    token = jwt_encode(users[0], settings_fixture)

    # Test pagination
    response = client.get("/api/v1/users/?limit=2&offset=0", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 3
    assert len(data["items"]) == 2

    # Test search
    response = client.get("/api/v1/users/?search=Bob", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["items"][0]["username"] == "bob"


@pytest.mark.asyncio
async def test_user_can_delete_own_account(db_fixture: AsyncSession, settings_fixture: Settings):
    user: User = UserFactory.build(password__raw="testpassword")
    db_fixture.add(user)
    await db_fixture.commit()
    await db_fixture.refresh(user)

    token = jwt_encode(user, settings_fixture)
    response = client.delete(f"/api/v1/users/{user.id}", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 204

    # Verify user is deleted
    stmt = select(User).where(User.id == user.id)
    result = await db_fixture.execute(stmt)
    deleted_user = result.scalar_one_or_none()
    assert deleted_user is None


@pytest.mark.asyncio
async def test_user_cannot_delete_other_user_account(db_fixture: AsyncSession, settings_fixture: Settings):
    user1: User = UserFactory.build(password__raw="password1")
    user2: User = UserFactory.build(password__raw="password2")
    db_fixture.add_all([user1, user2])
    await db_fixture.commit()
    await db_fixture.refresh(user1)
    await db_fixture.refresh(user2)

    token = jwt_encode(user1, settings_fixture)
    response = client.delete(f"/api/v1/users/{user2.id}", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403
    assert response.json() == {"detail": "Not authorized to delete this user"}


@pytest.mark.asyncio
async def test_user_can_update_own_profile(db_fixture: AsyncSession, settings_fixture: Settings):
    user: User = UserFactory.build(password__raw="testpassword", first_name="OldFirst", last_name="OldLast")
    db_fixture.add(user)
    await db_fixture.commit()
    await db_fixture.refresh(user)

    token = jwt_encode(user, settings_fixture)
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
async def test_user_cannot_update_other_user_profile(db_fixture: AsyncSession, settings_fixture: Settings):
    user1: User = UserFactory.build(password__raw="password1", first_name="First1", last_name="Last1")
    user2: User = UserFactory.build(password__raw="password2", first_name="First2", last_name="Last2")
    db_fixture.add_all([user1, user2])
    await db_fixture.commit()
    await db_fixture.refresh(user1)
    await db_fixture.refresh(user2)

    token = jwt_encode(user1, settings_fixture)
    update_data = {"first_name": "HackedFirst", "last_name": "HackedLast"}
    response = client.put(
        f"/api/v1/users/{user2.id}",
        json=update_data,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Not authorized to update this user"}

    # Verify no changes in the database
    stmt = select(User).where(User.id == user2.id)
    result = await db_fixture.execute(stmt)
    untouched_user = result.scalar_one()
    assert untouched_user.first_name == "First2"
    assert untouched_user.last_name == "Last2"
