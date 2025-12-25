import uuid
from fastapi import APIRouter, status
from pydantic import BaseModel

from app.config.auth import CurrentUserDep
from app.config.exceptions import raises
from app.features.users.models import UserType


class MeOutput(BaseModel):
    id: uuid.UUID
    type: UserType
    username: str
    first_name: str
    last_name: str


router = APIRouter()

# Me endpoint
# ----------------------------------------------------------------------------------------------------------------------


@raises(status.HTTP_401_UNAUTHORIZED)
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
