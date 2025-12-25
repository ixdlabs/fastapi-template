import logging
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.config.audit_log import AuditLoggerDep
from app.config.auth import CurrentUserDep
from app.config.database import DbDep
from app.config.exceptions import raises
from app.features.users.models import User

logger = logging.getLogger(__name__)


class ChangePasswordInput(BaseModel):
    old_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=1, max_length=128)


class ChangePasswordOutput(BaseModel):
    detail: str = "Password change successful."


router = APIRouter()

# Change Password endpoint
# ----------------------------------------------------------------------------------------------------------------------


@raises(status.HTTP_400_BAD_REQUEST)
@raises(status.HTTP_401_UNAUTHORIZED)
@raises(status.HTTP_404_NOT_FOUND)
@router.post("/change-password")
async def change_password(
    form: ChangePasswordInput, current_user: CurrentUserDep, db: DbDep, audit_logger: AuditLoggerDep
) -> ChangePasswordOutput:
    """Change the password for the current user."""
    stmt = select(User).where(User.id == current_user.id)
    result = await db.execute(stmt)
    user = result.scalar_one()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if not user.check_password(form.old_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Old password is incorrect.")
    if form.old_password == form.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="New password must be different from old password."
        )

    user.set_password(form.new_password)
    await audit_logger.record("change_password", user)
    await db.commit()

    return ChangePasswordOutput()
