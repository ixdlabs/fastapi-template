import pytest
from fastapi.testclient import TestClient
from app.features.users.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession

URL = "/api/v1/common/users/me"


@pytest.mark.asyncio
async def test_user_can_access_own_detail(test_client_fixture: TestClient, authenticated_user_fixture: User):
    response = test_client_fixture.get(URL)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(authenticated_user_fixture.id)
    assert data["username"] == authenticated_user_fixture.username


@pytest.mark.asyncio
async def test_user_cannot_access_detail_if_deleted(
    test_client_fixture: TestClient, db_fixture: AsyncSession, authenticated_user_fixture: User
):
    assert authenticated_user_fixture is not None

    await db_fixture.delete(authenticated_user_fixture)
    await db_fixture.commit()

    response = test_client_fixture.get(URL)
    assert response.status_code == 404
    assert response.json()["type"] == "users/common/detail-me/user-not-found"
