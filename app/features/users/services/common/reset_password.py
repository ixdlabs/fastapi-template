import logging
from fastapi import APIRouter
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select

from app.config.background import BackgroundDep
from app.config.database import DbDep
from app.features.users.models.user import User
from app.features.users.services.tasks.send_password_reset_email import SendPasswordResetInput
from app.features.users.tasks import send_password_reset_email_task

logger = logging.getLogger(__name__)
router = APIRouter()


# Input/Output
# ----------------------------------------------------------------------------------------------------------------------


class ResetPasswordInput(BaseModel):
    email: EmailStr = Field(...)


class ResetPasswordOutput(BaseModel):
    detail: str = "If the email exists, a password reset link has been sent."


# Password Reset endpoint
# ----------------------------------------------------------------------------------------------------------------------


@router.post("/reset-password")
async def reset_password(form: ResetPasswordInput, db: DbDep, background: BackgroundDep) -> ResetPasswordOutput:
    """
    Initiate a password reset by sending a reset email to the user's email address.
    If the email does not exist, the response is the same to avoid disclosing user existence.
    The user must have a verified email to receive the reset email.
    """
    # Retrieve the user by email
    stmt = select(User).where(User.email == form.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        logger.info(f"Password reset requested for non-existent email: {form.email}")
        return ResetPasswordOutput()

    # Submit background task
    task_input = SendPasswordResetInput(user_id=user.id, email=form.email)
    await background.submit(send_password_reset_email_task, task_input.model_dump_json())
    logger.info("Password reset email task submitted", extra={"user_id": str(user.id), "email": form.email})
    return ResetPasswordOutput()
