from datetime import datetime
import uuid
import typing

from argon2 import PasswordHasher
from argon2.exceptions import Argon2Error

from app.config.database import Base
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy import UUID, String, DateTime

if typing.TYPE_CHECKING:
    from app.features.notifications.models import Notification


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String, unique=True)
    first_name: Mapped[str] = mapped_column(String)
    last_name: Mapped[str] = mapped_column(String)
    hashed_password: Mapped[str] = mapped_column(String)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    notifications: Mapped[list["Notification"]] = relationship(back_populates="user", passive_deletes=True)

    def set_password(self, password: str):
        password_hasher = PasswordHasher()
        self.hashed_password = password_hasher.hash(password)

    def check_password(self, password: str) -> bool:
        password_hasher = PasswordHasher()
        try:
            return password_hasher.verify(self.hashed_password, password)
        except Argon2Error:
            return False
