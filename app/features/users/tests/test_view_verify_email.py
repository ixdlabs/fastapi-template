import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.users.models import User, UserEmailVerification, UserEmailVerificationState
from app.features.users.tests.fixtures import UserEmailVerificationFactory, UserFactory
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.mark.asyncio
async def test_verify_email_success(db_fixture: AsyncSession):
    user: User = UserFactory.build(email="old@example.com")
    db_fixture.add(user)
    await db_fixture.commit()
    await db_fixture.refresh(user)

    verification: UserEmailVerification = UserEmailVerificationFactory.build(user_id=user.id, email="new@example.com")
    verification.set_verification_token("valid-token")
    db_fixture.add(verification)
    await db_fixture.commit()
    await db_fixture.refresh(verification)

    response = client.post(
        "/api/auth/verify-email",
        json={"verification_id": str(verification.id), "token": "valid-token"},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["user_id"] == str(user.id)
    assert data["email"] == "new@example.com"

    await db_fixture.refresh(user)
    await db_fixture.refresh(verification)

    assert user.email == "new@example.com"
    assert verification.state == UserEmailVerificationState.VERIFIED


@pytest.mark.asyncio
async def test_verify_email_verification_not_found(db_fixture: AsyncSession):
    response = client.post(
        "/api/auth/verify-email",
        json={"verification_id": str(uuid.uuid4()), "token": "any-token"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Verification not found"


@pytest.mark.asyncio
async def test_verify_email_invalid_token(db_fixture: AsyncSession):
    user: User = UserFactory.build(email="old@example.com")
    db_fixture.add(user)
    await db_fixture.commit()
    await db_fixture.refresh(user)

    verification: UserEmailVerification = UserEmailVerificationFactory.build(user_id=user.id, email="new@example.com")
    verification.set_verification_token("correct-token")

    db_fixture.add(verification)
    await db_fixture.commit()
    await db_fixture.refresh(verification)

    response = client.post(
        "/api/auth/verify-email",
        json={"verification_id": str(verification.id), "token": "wrong-token"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid verification token"


@pytest.mark.asyncio
async def test_verify_email_user_not_found(db_fixture: AsyncSession):
    verification: UserEmailVerification = UserEmailVerificationFactory.build(
        user_id=uuid.uuid4(), email="new@example.com"
    )
    verification.set_verification_token("valid-token")

    db_fixture.add(verification)
    await db_fixture.commit()
    await db_fixture.refresh(verification)

    response = client.post(
        "/api/auth/verify-email",
        json={"verification_id": str(verification.id), "token": "valid-token"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


@pytest.mark.asyncio
async def test_verify_email_email_already_in_use(db_fixture: AsyncSession):
    user1: User = UserFactory.build(email="user1@example.com")
    user2: User = UserFactory.build(email="user2@example.com")

    db_fixture.add_all([user1, user2])
    await db_fixture.commit()
    await db_fixture.refresh(user1)
    await db_fixture.refresh(user2)

    verification: UserEmailVerification = UserEmailVerificationFactory.build(
        user_id=user1.id, email="user2@example.com"
    )
    verification.set_verification_token("valid-token")

    db_fixture.add(verification)
    await db_fixture.commit()
    await db_fixture.refresh(verification)

    response = client.post(
        "/api/auth/verify-email",
        json={"verification_id": str(verification.id), "token": "valid-token"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Email already in use by another user"


@pytest.mark.asyncio
async def test_verify_email_already_verified(db_fixture: AsyncSession):
    user: User = UserFactory.build(email="old@example.com")
    db_fixture.add(user)
    await db_fixture.commit()
    await db_fixture.refresh(user)

    verification: UserEmailVerification = UserEmailVerificationFactory.build(
        user_id=user.id,
        email="new@example.com",
        state=UserEmailVerificationState.VERIFIED,
    )
    verification.set_verification_token("valid-token")

    db_fixture.add(verification)
    await db_fixture.commit()
    await db_fixture.refresh(verification)

    response = client.post(
        "/api/auth/verify-email",
        json={"verification_id": str(verification.id), "token": "valid-token"},
    )

    assert response.status_code == 400
