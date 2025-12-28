import uuid
from fastapi import APIRouter, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.auth import AuthenticatorDep
from app.core.database import DbDep
from app.core.exceptions import ServiceException, raises
from app.features.users.models.user import User, UserType


router = APIRouter()


# Input/Output
# ----------------------------------------------------------------------------------------------------------------------


class LoginInput(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=1, max_length=128)


class LoginOutput(BaseModel):
    access_token: str
    refresh_token: str
    user: "LoginOutputUser"


class LoginOutputUser(BaseModel):
    id: uuid.UUID
    type: UserType
    username: str
    first_name: str
    last_name: str


# Exceptions
# ----------------------------------------------------------------------------------------------------------------------


class InvalidUsernameOrPasswordException(ServiceException):
    status_code = status.HTTP_401_UNAUTHORIZED
    type = "users/common/login/invalid-credentials"
    detail = "Invalid username or password, please check your credentials and try again"


# Login endpoint
# ----------------------------------------------------------------------------------------------------------------------


@raises(InvalidUsernameOrPasswordException)
@router.post("/login")
async def login(form: LoginInput, db: DbDep, authenticator: AuthenticatorDep) -> LoginOutput:
    """Login a user and return access and refresh tokens."""
    # Fetch user by username
    stmt = select(User).where(User.username == form.username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise InvalidUsernameOrPasswordException()

    # Verify password
    password_valid = user.check_password(form.password)
    if not password_valid:
        raise InvalidUsernameOrPasswordException()

    # Generate tokens
    access_token, refresh_token = authenticator.encode(user)
    return LoginOutput(
        access_token=access_token,
        refresh_token=refresh_token,
        user=LoginOutputUser(
            id=user.id,
            type=user.type,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
        ),
    )
