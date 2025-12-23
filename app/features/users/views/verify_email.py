import uuid
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.config.database import DbDep
from app.config.exceptions import raises
from app.features.users.models import User, UserEmailVerification, UserEmailVerificationState


class VerifyEmailInput(BaseModel):
    verification_id: uuid.UUID = Field(...)
    token: str = Field(..., min_length=1, max_length=128)


class VerifyEmailOutput(BaseModel):
    user_id: uuid.UUID
    email: str


router = APIRouter()

# Verify Email endpoint
# ----------------------------------------------------------------------------------------------------------------------


@raises(status.HTTP_400_BAD_REQUEST)
@raises(status.HTTP_404_NOT_FOUND)
@router.post("/verify-email")
async def verify_email(form: VerifyEmailInput, db: DbDep) -> VerifyEmailOutput:
    """Verify email of a user using the generated token."""
    # Retrieve the verification record
    stmt = select(UserEmailVerification).where(UserEmailVerification.id == form.verification_id)
    result = await db.execute(stmt)
    verification = result.scalar_one_or_none()
    if verification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Verification not found")
    if not verification.is_valid(form.token):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification token")

    # Retrieve the user associated with the verification
    user_stmt = select(User).where(User.id == verification.user_id)
    user_result = await db.execute(user_stmt)
    user = user_result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Check if email is already used by another user
    email_other_stmt = select(User).where(User.email == verification.email).where(User.id != user.id)
    email_other_result = await db.execute(email_other_stmt)
    email_other_user = email_other_result.scalar_one_or_none()
    if email_other_user is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already in use by another user")

    # Update user email and verification state
    user.email = verification.email
    verification.state = UserEmailVerificationState.VERIFIED
    db.add(user)
    db.add(verification)
    await db.commit()
    await db.refresh(user)

    return VerifyEmailOutput(user_id=user.id, email=user.email)
