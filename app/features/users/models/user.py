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
from sqlalchemy import UUID, Enum, String

from app.config.timezone import DateTimeUTC, utc_now

if typing.TYPE_CHECKING:
    from app.features.users.models.user_action import UserAction
    from app.features.notifications.models.notification import Notification


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

    def get_oauth2_scopes(self) -> set[str]:
        """Return the OAuth2 scopes associated with this user based on their type."""
        if self.type == UserType.ADMIN:
            return {"admin", "user"}
        elif self.type == UserType.CUSTOMER:
            return {"customer", "user"}
        else:
            return {"user"}
