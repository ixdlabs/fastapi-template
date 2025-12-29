import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.testclient import TestClient
from app.features.users.models.user import UserType, User
from app.fixtures.user_factory import UserFactory

BASE_URL = "/api/v1/admin/users"


@pytest.mark.asyncio
async def test_admin_can_access_other_user_detail(
    test_client_fixture: TestClient, db_fixture: AsyncSession, authenticated_admin_fixture: User
):
    assert authenticated_admin_fixture.type == UserType.ADMIN

    user1: User = UserFactory.build(password__raw="userpassword")
    db_fixture.add(user1)
    await db_fixture.commit()
    await db_fixture.refresh(user1)

    response = test_client_fixture.get(f"{BASE_URL}/{user1.id}")
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == str(user1.id)
    assert data["username"] == user1.username


@pytest.mark.asyncio
async def test_admin_cannot_access_nonexistent_user(test_client_fixture: TestClient, authenticated_admin_fixture: User):
    assert authenticated_admin_fixture.type == UserType.ADMIN

    response = test_client_fixture.get(f"{BASE_URL}/{uuid.uuid4()}")
    assert response.status_code == 404
    assert response.json()["type"] == "users/admin/detail-user/user-not-found"
