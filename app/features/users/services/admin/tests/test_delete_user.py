import uuid
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.testclient import TestClient
from app.features.users.models.user import UserType, User
from app.fixtures.user_factory import UserFactory

BASE_URL = "/api/v1/admin/users"


@pytest.mark.asyncio
async def test_admin_can_delete_other_user_account(
    test_client_fixture: TestClient, db_fixture: AsyncSession, authenticated_admin_fixture: User
):
    assert authenticated_admin_fixture.type == UserType.ADMIN

    user1: User = UserFactory.build(password__raw="userpassword")
    db_fixture.add(user1)
    await db_fixture.commit()
    await db_fixture.refresh(user1)

    response = test_client_fixture.delete(f"{BASE_URL}/{user1.id}")
    assert response.status_code == 204

    stmt = select(User).where(User.id == user1.id)
    result = await db_fixture.execute(stmt)
    deleted_user = result.scalar_one_or_none()
    assert deleted_user is None


@pytest.mark.asyncio
async def test_admin_cannot_delete_nonexistent_user(test_client_fixture: TestClient, authenticated_admin_fixture: User):
    assert authenticated_admin_fixture.type == UserType.ADMIN

    response = test_client_fixture.delete(f"{BASE_URL}/{uuid.uuid4()}")
    assert response.status_code == 404
    assert response.json()["type"] == "users/admin/delete-user/user-not-found"
