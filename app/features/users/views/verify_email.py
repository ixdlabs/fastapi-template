import uuid
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.config.audit_log import AuditLoggerDep
from app.config.database import DbDep
from app.config.exceptions import raises
from app.features.users.models import User, UserAction, UserActionState, UserActionType


class VerifyEmailInput(BaseModel):
    action_id: uuid.UUID = Field(...)
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
async def verify_email(form: VerifyEmailInput, db: DbDep, audit_logger: AuditLoggerDep) -> VerifyEmailOutput:
    """Verify email of a user using the generated token."""
    # Retrieve the action record
    stmt = select(UserAction).where(UserAction.id == form.action_id)
    result = await db.execute(stmt)
    action = result.scalar_one_or_none()
    if action is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action not found")
    if action.type != UserActionType.EMAIL_VERIFICATION:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid action type")
    if not action.is_valid(form.token):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid action token")

    if action.data is None or "email" not in action.data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Action data is missing email")
    action_email = action.data["email"]

    # Retrieve the user associated with the action
    user_stmt = select(User).where(User.id == action.user_id)
    user_result = await db.execute(user_stmt)
    user = user_result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Check if email is already used by another user
    email_other_stmt = select(User).where(User.email == action_email).where(User.id != user.id)
    email_other_result = await db.execute(email_other_stmt)
    email_other_user = email_other_result.scalar_one_or_none()
    if email_other_user is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already in use by another user")

    # Update user email and action state
    await audit_logger.track(user)
    user.email = action_email
    action.state = UserActionState.COMPLETED
    db.add(user)
    db.add(action)

    await audit_logger.record("verify_email", user)
    await db.commit()
    await db.refresh(user)

    return VerifyEmailOutput(user_id=user.id, email=user.email)
