import uuid
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
import logging

from app.config.auth import AuthenticatorDep, AuthException
from app.config.database import DbDep
from app.features.users.models import User

logger = logging.getLogger(__name__)


class RefreshInput(BaseModel):
    refresh_token: str


class RefreshOutput(BaseModel):
    access_token: str
    refresh_token: str
    user: "RefreshOutputUser"


class RefreshOutputUser(BaseModel):
    id: uuid.UUID
    username: str
    first_name: str
    last_name: str


router = APIRouter()


# Refresh endpoint
# ----------------------------------------------------------------------------------------------------------------------


@router.post("/refresh")
async def refresh(form: RefreshInput, db: DbDep, authenticator: AuthenticatorDep) -> RefreshOutput:
    """Refresh the user's tokens using refresh token."""
    try:
        user_id = authenticator.sub(form.refresh_token)
    except AuthException as e:
        logger.warning("token validation failed", exc_info=True)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials") from e

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    access_token, refresh_token = authenticator.encode(user)
    return RefreshOutput(
        access_token=access_token,
        refresh_token=refresh_token,
        user=RefreshOutputUser(
            id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
        ),
    )
