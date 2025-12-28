from datetime import datetime, timezone
import enum
import uuid
import typing

from argon2 import PasswordHasher
from argon2.exceptions import Argon2Error

from app.core.database import Base
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy import JSON, UUID, Enum, ForeignKey, String

from app.core.timezone import DateTimeUTC, utc_now

if typing.TYPE_CHECKING:
    from app.features.users.models.user import User


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

    data: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
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
