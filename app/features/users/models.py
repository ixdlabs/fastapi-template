from datetime import datetime
import enum
import uuid
import typing

from argon2 import PasswordHasher
from argon2.exceptions import Argon2Error

from app.config.database import Base
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy import UUID, Enum, String, DateTime

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

    first_name: Mapped[str] = mapped_column(String)
    last_name: Mapped[str] = mapped_column(String)
    hashed_password: Mapped[str] = mapped_column(String)

    email: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    email_verified: Mapped[bool] = mapped_column(default=False)

    joined_at: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    notifications: Mapped[list["Notification"]] = relationship(
        back_populates="user", passive_deletes=True, lazy="noload"
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


class UserEmailVerificationState(enum.Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    OBSELETE = "obselete"


class UserEmailVerification(Base):
    __tablename__ = "user_email_verifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID)
    state: Mapped[UserEmailVerificationState] = mapped_column(Enum(UserEmailVerificationState))

    email: Mapped[str] = mapped_column(String)
    hashed_verification_token: Mapped[str] = mapped_column(String)

    expires_at: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    def set_verification_token(self, token: str):
        password_hasher = PasswordHasher()
        self.hashed_verification_token = password_hasher.hash(token)

    def is_valid(self, verification_token: str) -> bool:
        if self.state != UserEmailVerificationState.PENDING:
            return False
        if self.expires_at < datetime.now():
            return False

        password_hasher = PasswordHasher()
        try:
            return password_hasher.verify(self.hashed_verification_token, verification_token)
        except Argon2Error:
            return False
