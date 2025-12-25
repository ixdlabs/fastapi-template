import uuid
from fastapi import APIRouter
from pydantic import BaseModel

from app.config.auth import AuthenticationFailedException, CurrentUserDep
from app.config.exceptions import raises
from app.features.users.models import UserType


# Input/Output
# ----------------------------------------------------------------------------------------------------------------------


class MeOutput(BaseModel):
    id: uuid.UUID
    type: UserType
    username: str
    first_name: str
    last_name: str


# Me endpoint
# ----------------------------------------------------------------------------------------------------------------------


router = APIRouter()


@raises(AuthenticationFailedException)
@router.get("/me")
async def get_me(current_user: CurrentUserDep) -> MeOutput:
    """Get the current authenticated user's information."""
    return MeOutput(
        id=current_user.id,
        type=current_user.type,
        username=current_user.username,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
    )
