from datetime import datetime, timezone
import enum
import uuid
import typing
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import Argon2Error

from app.config.database import Base
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy import JSON, UUID, Enum, String

from app.config.timezone import DateTimeUTC, utc_now

if typing.TYPE_CHECKING:
    from app.features.notifications.models import Notification


class UserType(enum.Enum):
    ADMIN = "admin"
    CUSTOMER = "customer"


# User
# ----------------------------------------------------------------------------------------------------------------------


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    type: Mapped[UserType] = mapped_column(Enum(UserType))
    username: Mapped[str] = mapped_column(String, unique=True)
    email: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)

    first_name: Mapped[str] = mapped_column(String)
    last_name: Mapped[str] = mapped_column(String)
    hashed_password: Mapped[str] = mapped_column(String)

    joined_at: Mapped[datetime] = mapped_column(DateTimeUTC)
    created_at: Mapped[datetime] = mapped_column(DateTimeUTC, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTimeUTC, default=utc_now, onupdate=utc_now)

    notifications: Mapped[list["Notification"]] = relationship(
        back_populates="user", passive_deletes=True, lazy="raise_on_sql"
    )

    def set_password(self, password: str):
        password_hasher = PasswordHasher()
        self.hashed_password = password_hasher.hash(password)

    def check_password(self, password: str) -> bool:
        password_hasher = PasswordHasher()
        try:
            return password_hasher.verify(self.hashed_password, password)
        except Argon2Error:
            return False


# User Email Verification
# ----------------------------------------------------------------------------------------------------------------------


class UserActionType(enum.Enum):
    EMAIL_VERIFICATION = "email_verification"
    PASSWORD_RESET = "password_reset"


class UserActionState(enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    OBSOLETE = "obsolete"


class UserAction(Base):
    __tablename__ = "user_actions"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    type: Mapped[UserActionType] = mapped_column(Enum(UserActionType))
    state: Mapped[UserActionState] = mapped_column(Enum(UserActionState), default=UserActionState.PENDING)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID)

    data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    hashed_token: Mapped[str] = mapped_column(String)

    expires_at: Mapped[datetime] = mapped_column(DateTimeUTC)
    created_at: Mapped[datetime] = mapped_column(DateTimeUTC, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTimeUTC, default=utc_now, onupdate=utc_now)

    def set_token(self, token: str):
        password_hasher = PasswordHasher()
        self.hashed_token = password_hasher.hash(token)

    def is_valid(self, token: str) -> bool:
        if self.state != UserActionState.PENDING:
            return False
        if self.expires_at < datetime.now(timezone.utc):
            return False

        password_hasher = PasswordHasher()
        try:
            return password_hasher.verify(self.hashed_token, token)
        except Argon2Error:
            return False
