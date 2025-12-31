import logging
from fastapi import APIRouter, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select

from app.core.auth import AuthenticationFailedException, CurrentUserDep
from app.core.database import DbDep
from app.core.exceptions import ServiceException, raises
from app.core.storage import convert_uploaded_file_to_db
from app.features.users.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


# Input/Output
# ----------------------------------------------------------------------------------------------------------------------


class ChangeProfilePictureOutput(BaseModel):
    detail: str = "Profile picture change successful."


# Exceptions
# ----------------------------------------------------------------------------------------------------------------------


class UserNotFoundException(ServiceException):
    status_code = status.HTTP_404_NOT_FOUND
    type = "users/common/change-password/user-not-found"
    detail = "User not found, your account may have been deleted"


# Change Profile Picture endpoint
# ----------------------------------------------------------------------------------------------------------------------


@raises(AuthenticationFailedException)
@raises(UserNotFoundException)
@router.post("/change-profile-picture")
async def change_profile_picture(
    profile_picture: UploadFile, current_user: CurrentUserDep, db: DbDep
) -> ChangeProfilePictureOutput:
    """
    Change the profile picture for the current user.
    """
    # Fetch the current user from the database
    stmt = select(User).where(User.id == current_user.id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise UserNotFoundException()

    # Update the user's profile picture
    user.profile_picture = await convert_uploaded_file_to_db(profile_picture)
    db.add(user)
    await db.commit()

    return ChangeProfilePictureOutput()
