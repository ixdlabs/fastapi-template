import uuid
from fastapi import APIRouter, status
from pydantic import BaseModel

from app.config.auth import CurrentUserDep
from app.config.exceptions import raises


class MeOutput(BaseModel):
    id: uuid.UUID
    username: str
    first_name: str
    last_name: str


router = APIRouter()

# Me endpoint
# ----------------------------------------------------------------------------------------------------------------------


@raises(status.HTTP_401_UNAUTHORIZED)
@router.get("/me")
async def me(current_user: CurrentUserDep) -> MeOutput:
    """Get details of the current authenticated user."""
    return MeOutput(
        id=current_user.id,
        username=current_user.username,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
    )
