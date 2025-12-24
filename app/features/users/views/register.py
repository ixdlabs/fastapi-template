from datetime import datetime, timezone
import uuid
from fastapi import APIRouter, HTTPException, status
from pydantic import AwareDatetime, BaseModel, EmailStr, Field
from sqlalchemy import select

from app.config.audit_log import AuditLoggerDep
from app.config.auth import AuthenticatorDep
from app.config.background import BackgroundDep
from app.config.database import DbDep
from app.config.exceptions import raises
from app.features.users.models import User, UserType
from app.features.users.tasks.email_verification import SendEmailVerificationInput, send_email_verification_email_task


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
    joined_at: AwareDatetime


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
    # Check if username or email already exists
    username_check_stmt = select(User).where(User.username == form.username)
    username_check_result = await db.execute(username_check_stmt)
    username_check_user = username_check_result.scalar_one_or_none()
    if username_check_user is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")

    # Check email if provided
    if form.email is not None:
        email_check_stmt = select(User).where(User.email == form.email)
        email_check_result = await db.execute(email_check_stmt)
        email_check_user = email_check_result.scalar_one_or_none()
        if email_check_user is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")

    # Create user
    user = User(
        id=uuid.uuid4(),
        username=form.username,
        type=UserType.CUSTOMER,
        first_name=form.first_name,
        last_name=form.last_name,
        joined_at=datetime.now(timezone.utc),
    )
    user.set_password(form.password)
    await audit_logger.add("create", user)

    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Send email verification if email provided
    if form.email is not None:
        task_input = SendEmailVerificationInput(user_id=user.id, email=form.email)
        await background.submit(send_email_verification_email_task, task_input.model_dump_json())

    # Generate tokens and return response
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
            joined_at=user.joined_at,
        ),
    )
