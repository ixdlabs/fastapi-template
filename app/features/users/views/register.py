from datetime import datetime
import uuid
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select

from app.config.audit_log import AuditLoggerDep
from app.config.auth import AuthenticatorDep
from app.config.background import BackgroundDep
from app.config.database import DbDep
from app.config.exceptions import raises
from app.features.users.models import User, UserType
from app.features.users.tasks.email_verification import send_email_verification_email_task


class RegisterInput(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=1, max_length=128)
    first_name: str = Field(..., min_length=1, max_length=256)
    last_name: str = Field(..., min_length=1, max_length=256)
    email: EmailStr | None = Field(None, max_length=320)


class RegisterOutput(BaseModel):
    access_token: str
    refresh_token: str
    user: "RegisterOutputUser"


class RegisterOutputUser(BaseModel):
    id: uuid.UUID
    type: UserType
    username: str
    first_name: str
    last_name: str
    email: str | None
    joined_at: datetime


router = APIRouter()

# Register endpoint
# ----------------------------------------------------------------------------------------------------------------------


@raises(status.HTTP_400_BAD_REQUEST)
@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    form: RegisterInput,
    db: DbDep,
    authenticator: AuthenticatorDep,
    background: BackgroundDep,
    audit_logger: AuditLoggerDep,
) -> RegisterOutput:
    """Register a new user."""
    username_check_stmt = select(User).where(User.username == form.username)
    username_check_result = await db.execute(username_check_stmt)
    username_check_user = username_check_result.scalar_one_or_none()
    if username_check_user is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")

    if form.email is not None:
        email_check_stmt = select(User).where(User.email == form.email)
        email_check_result = await db.execute(email_check_stmt)
        email_check_user = email_check_result.scalar_one_or_none()
        if email_check_user is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")

    user = User(
        username=form.username,
        type=UserType.CUSTOMER,
        first_name=form.first_name,
        last_name=form.last_name,
        email=form.email,
        email_verified=False,
        joined_at=datetime.now(),
    )
    user.set_password(form.password)

    db.add(user)
    await db.commit()
    await db.refresh(user)

    await audit_logger.log("create", new_resource=user, exclude_columns=["hashed_password"])
    if user.email is not None:
        await background.submit(send_email_verification_email_task, user.id)

    access_token, refresh_token = authenticator.encode(user)
    return RegisterOutput(
        access_token=access_token,
        refresh_token=refresh_token,
        user=RegisterOutputUser(
            id=user.id,
            type=user.type,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email,
            joined_at=user.joined_at,
        ),
    )
