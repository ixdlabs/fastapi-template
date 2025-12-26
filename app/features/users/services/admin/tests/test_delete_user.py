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
async def test_admin_can_delete_other_user_account(db_fixture: AsyncSession, authenticated_admin_fixture: User):
    assert authenticated_admin_fixture.type == UserType.ADMIN

    user1: User = UserFactory.build(password__raw="userpassword")
    db_fixture.add(user1)
    await db_fixture.commit()
    await db_fixture.refresh(user1)

    response = client.delete(f"{base_url}/{user1.id}")
    assert response.status_code == 204

    stmt = select(User).where(User.id == user1.id)
    result = await db_fixture.execute(stmt)
    deleted_user = result.scalar_one_or_none()
    assert deleted_user is None


@pytest.mark.asyncio
async def test_admin_cannot_delete_nonexistent_user(authenticated_admin_fixture: User):
    assert authenticated_admin_fixture.type == UserType.ADMIN

    response = client.delete(f"{base_url}/{uuid.uuid4()}")
    assert response.status_code == 404
    assert response.json()["type"] == "users/admin/delete-user/user-not-found"
