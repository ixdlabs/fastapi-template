import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.testclient import TestClient
from app.features.users.models.user import User

URL = "/api/v1/common/users/me"


@pytest.mark.asyncio
async def test_user_can_delete_own_account(
    test_client_fixture: TestClient, db_fixture: AsyncSession, authenticated_user_fixture: User
):
    response = test_client_fixture.delete(URL)
    assert response.status_code == 204

    stmt = select(User).where(User.id == authenticated_user_fixture.id)
    result = await db_fixture.execute(stmt)
    deleted_user = result.scalar_one_or_none()
    assert deleted_user is None


@pytest.mark.asyncio
async def test_user_cannot_delete_account_if_already_deleted(
    test_client_fixture: TestClient, db_fixture: AsyncSession, authenticated_user_fixture: User
):
    assert authenticated_user_fixture is not None

    await db_fixture.delete(authenticated_user_fixture)
    await db_fixture.commit()

    response = test_client_fixture.delete(URL)
    assert response.status_code == 404
    assert response.json()["type"] == "users/common/delete-me/user-not-found"
