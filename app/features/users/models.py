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
from sqlalchemy import JSON, UUID, Enum, ForeignKey, String

from app.config.timezone import DateTimeUTC, utc_now

if typing.TYPE_CHECKING:
    from app.features.notifications.models import Notification


# User
# This is the primary user model representing users in the system. Login is based on username.
# Email is optional and unique and kept primarily for forgot password flows (email has to be verified before being set).
# ----------------------------------------------------------------------------------------------------------------------


class UserType(enum.Enum):
    ADMIN = "admin"
    CUSTOMER = "customer"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    type: Mapped[UserType] = mapped_column(Enum(UserType))
    username: Mapped[str] = mapped_column(String, unique=True)

    # This system follows the pattern of emails being unique but optional.
    # As a result, only one user can have a given email at a time, but users can have no email at all.
    # This is acceptable since the login identifier is the username, not the email.
    # To make sure the email is not locked down unnecessarily, the email is set only when the user verifies it.
    # Until then the email field is null and the email under verification is stored in the UserAction data.
    #
    # But in case of adapting to a system where email is required, unique, and used for login,
    # email can be set at registration and a separate flag can be used to indicate whether it's verified or not.
    # Then the email verification process would only update the flag to verified.
    email: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)

    first_name: Mapped[str] = mapped_column(String)
    last_name: Mapped[str] = mapped_column(String)
    hashed_password: Mapped[str] = mapped_column(String)

    joined_at: Mapped[datetime] = mapped_column(DateTimeUTC)
    created_at: Mapped[datetime] = mapped_column(DateTimeUTC, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTimeUTC, default=utc_now, onupdate=utc_now)

    actions: Mapped[list["UserAction"]] = relationship(back_populates="user", passive_deletes=True, lazy="raise_on_sql")
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


# User Action
# User actions represent one-time actions that users can perform, such as email verification or password reset.
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
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))

    data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    hashed_token: Mapped[str] = mapped_column(String)

    expires_at: Mapped[datetime] = mapped_column(DateTimeUTC)
    created_at: Mapped[datetime] = mapped_column(DateTimeUTC, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTimeUTC, default=utc_now, onupdate=utc_now)

    user: Mapped["User"] = relationship(back_populates="actions", lazy="raise_on_sql")

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
