import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.testclient import TestClient
from app.conftest import NoOpTaskTrackingBackground
from app.features.users.models.user import User
from app.fixtures.user_factory import UserFactory

from app.main import app

client = TestClient(app)
url = "/api/v1/common/users/me"


@pytest.mark.asyncio
async def test_user_can_update_own_profile(db_fixture: AsyncSession, authenticated_user_fixture: User):
    update_data = {"first_name": "NewFirst", "last_name": "NewLast"}
    response = client.put(url, json=update_data)

    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "NewFirst"
    assert data["last_name"] == "NewLast"

    stmt = select(User).where(User.id == authenticated_user_fixture.id)
    result = await db_fixture.execute(stmt)
    updated_user = result.scalar_one()
    assert updated_user.first_name == "NewFirst"
    assert updated_user.last_name == "NewLast"


@pytest.mark.asyncio
async def test_user_can_update_email_triggers_verification(
    authenticated_user_fixture: User, background_fixture: NoOpTaskTrackingBackground
):
    update_data = {"first_name": "NewFirst", "last_name": "NewLast", "email": "newemail@example.com"}
    response = client.put(url, json=update_data)
    assert response.status_code == 200

    data = response.json()
    assert data["first_name"] == "NewFirst"
    assert data["last_name"] == "NewLast"
    assert data["email"] == authenticated_user_fixture.email  # Email not updated yet
    assert "send_email_verification_task" in background_fixture.called_tasks


@pytest.mark.asyncio
async def test_user_cannot_update_email_to_existing_email(db_fixture: AsyncSession, authenticated_user_fixture: User):
    assert authenticated_user_fixture is not None

    existing_user: User = UserFactory.build(email="existing@example.com")
    db_fixture.add(existing_user)
    await db_fixture.commit()
    await db_fixture.refresh(existing_user)
    await db_fixture.refresh(authenticated_user_fixture)

    update_data = {"first_name": "NewFirst", "last_name": "NewLast", "email": "existing@example.com"}
    response = client.put(url, json=update_data)
    assert response.status_code == 400
    assert response.json()["type"] == "users/common/update/email-exists"
