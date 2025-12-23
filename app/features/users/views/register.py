import uuid
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from app.config.audit_log import AuditLoggerDep
from app.config.auth import AuthenticatorDep
from app.config.background import BackgroundDep
from app.config.database import DbDep
from app.features.users.models import User
from app.features.users.tasks.welcome_email import send_welcome_email_task


class RegisterInput(BaseModel):
    username: str
    password: str
    first_name: str
    last_name: str


class RegisterOutput(BaseModel):
    access_token: str
    refresh_token: str
    user: "RegisterOutputUser"


class RegisterOutputUser(BaseModel):
    id: uuid.UUID
    username: str
    first_name: str
    last_name: str


router = APIRouter()

# Register endpoint
# ----------------------------------------------------------------------------------------------------------------------


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    form: RegisterInput,
    db: DbDep,
    authenticator: AuthenticatorDep,
    background: BackgroundDep,
    audit_logger: AuditLoggerDep,
) -> RegisterOutput:
    """Register a new user."""
    stmt = select(User).where(User.username == form.username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")

    user = User(username=form.username, first_name=form.first_name, last_name=form.last_name)
    user.set_password(form.password)

    db.add(user)
    await db.commit()
    await db.refresh(user)

    await audit_logger.log("create", new_resource=user, exclude_columns=["hashed_password"], db=db)

    await background.submit(send_welcome_email_task, user.id)

    access_token, refresh_token = authenticator.encode(user)
    return RegisterOutput(
        access_token=access_token,
        refresh_token=refresh_token,
        user=RegisterOutputUser(
            id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
        ),
    )
