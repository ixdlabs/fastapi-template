import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.testclient import TestClient
from app.config.auth import Authenticator
from app.features.users.models import UserType
from app.features.users.tests.fixtures import UserFactory
from app.main import app

client = TestClient(app)


@pytest.mark.asyncio
async def test_user_list_pagination_and_search(db_fixture: AsyncSession, authenticator_fixture: Authenticator):
    users = [
        UserFactory.build(
            username="alice", first_name="Alice", last_name="Anderson", type=UserType.ADMIN, password__raw="password1"
        ),
        UserFactory.build(username="bob", first_name="Bob", last_name="Brown", password__raw="password2"),
        UserFactory.build(username="charlie", first_name="Charlie", last_name="Clark", password__raw="password3"),
    ]
    db_fixture.add_all(users)
    await db_fixture.commit()
    for user in users:
        await db_fixture.refresh(user)

    token, _ = authenticator_fixture.encode(users[0])

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
