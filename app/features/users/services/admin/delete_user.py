import uuid
from fastapi import APIRouter, status
from sqlalchemy import select

from app.config.audit_log import AuditLoggerDep
from app.config.auth import AuthenticationFailedException, AuthorizationFailedException, CurrentAdminDep
from app.config.database import DbDep
from app.config.exceptions import ServiceException, raises
from app.features.users.models.user import UserType, User

router = APIRouter()


# Exceptions
# ----------------------------------------------------------------------------------------------------------------------


class UserNotFoundException(ServiceException):
    status_code = status.HTTP_404_NOT_FOUND
    type = "users/admin/delete-user/user-not-found"
    detail = "User not found"


# Delete user endpoint
# ----------------------------------------------------------------------------------------------------------------------


@raises(AuthenticationFailedException)
@raises(AuthorizationFailedException)
@raises(UserNotFoundException)
@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: uuid.UUID, db: DbDep, current_admin: CurrentAdminDep, audit_logger: AuditLoggerDep
) -> None:
    """
    Delete a user from the system.
    The authenticated user must be an admin.
    """
    assert current_admin.type == UserType.ADMIN

    # Fetch user from database
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise UserNotFoundException()

    await audit_logger.record("delete", user)
    await db.delete(user)
    await db.commit()
