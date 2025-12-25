import uuid
from fastapi import APIRouter, status
from sqlalchemy import select

from app.config.audit_log import AuditLoggerDep
from app.config.auth import AuthenticationFailedException, CurrentUserDep
from app.config.database import DbDep
from app.config.exceptions import ServiceException, raises
from app.features.users.models import User, UserType

router = APIRouter()


# Exceptions
# ----------------------------------------------------------------------------------------------------------------------


class UserDeleteNotAuthorizedException(ServiceException):
    status_code = status.HTTP_403_FORBIDDEN
    type = "users/delete-user/not-authorized"
    detail = "Not authorized to delete this user"


class UserNotFoundException(ServiceException):
    status_code = status.HTTP_404_NOT_FOUND
    type = "users/delete-user/user-not-found"
    detail = "User not found"


# Delete user endpoint
# ----------------------------------------------------------------------------------------------------------------------


@raises(AuthenticationFailedException)
@raises(UserDeleteNotAuthorizedException)
@raises(UserNotFoundException)
@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: uuid.UUID, db: DbDep, current_user: CurrentUserDep, audit_logger: AuditLoggerDep
) -> None:
    """
    Delete a user from the system.
    The authenticated user must be an admin or the user themselves.
    """
    # Authorization check
    if current_user.type != UserType.ADMIN and current_user.id != user_id:
        raise UserDeleteNotAuthorizedException()

    # Fetch user from database
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise UserNotFoundException()

    await audit_logger.record("delete", user)
    await db.delete(user)
    await db.commit()
