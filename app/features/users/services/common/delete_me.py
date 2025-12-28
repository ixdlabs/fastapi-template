from fastapi import APIRouter, status
from sqlalchemy import select

from app.core.audit_log import AuditLoggerDep
from app.core.auth import AuthenticationFailedException, CurrentUserDep
from app.core.database import DbDep
from app.core.exceptions import ServiceException, raises
from app.features.users.models.user import User

router = APIRouter()


# Exceptions
# ----------------------------------------------------------------------------------------------------------------------


class UserNotFoundException(ServiceException):
    status_code = status.HTTP_404_NOT_FOUND
    type = "users/common/delete-me/user-not-found"
    detail = "User not found, the account may have already been deleted"


# Delete user endpoint
# ----------------------------------------------------------------------------------------------------------------------


@raises(AuthenticationFailedException)
@raises(UserNotFoundException)
@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(db: DbDep, current_user: CurrentUserDep, audit_logger: AuditLoggerDep) -> None:
    """Delete the currently authenticated user."""
    # Fetch user from database
    stmt = select(User).where(User.id == current_user.id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise UserNotFoundException()

    await audit_logger.record("delete", user)
    await db.delete(user)
    await db.commit()
