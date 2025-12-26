import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.testclient import TestClient
from app.features.users.models.user import UserType, User
from app.fixtures.user_factory import UserFactory
from app.main import app

client = TestClient(app)
base_url = "/api/v1/admin/users"


async def create_users(db_fixture: AsyncSession):
    users = [
        UserFactory.build(username="alice", first_name="Alice", last_name="Anderson", password__raw="password1"),
        UserFactory.build(username="bob", first_name="Bob", last_name="Brown", password__raw="password2"),
        UserFactory.build(username="charlie", first_name="Charlie", last_name="Clark", password__raw="password3"),
    ]
    db_fixture.add_all(users)
    await db_fixture.commit()
    for user in users:
        await db_fixture.refresh(user)


# ----------------------------------------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_admin_can_list_users_with_pagination(db_fixture: AsyncSession, authenticated_admin_fixture: User):
    assert authenticated_admin_fixture.type == UserType.ADMIN

    await create_users(db_fixture)

    response = client.get(f"{base_url}/?limit=2&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 4  # Including the logged-in admin
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_admin_can_list_users_with_search(db_fixture: AsyncSession, authenticated_admin_fixture: User):
    assert authenticated_admin_fixture.type == UserType.ADMIN

    await create_users(db_fixture)

    response = client.get(f"{base_url}/?search=Bob")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["items"][0]["username"] == "bob"
