from datetime import datetime
import uuid
import enum
import typing

from app.config.database import Base

from sqlalchemy.types import Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import UUID, String, DateTime, JSON, ForeignKey
from typing import Any

if typing.TYPE_CHECKING:
    from app.features.users.models import User


class NotificationType(enum.Enum):
    CUSTOM = "custom"
    WELCOME = "welcome"


class NotificationChannel(enum.Enum):
    EMAIL = "email"
    SMS = "sms"
    INAPP = "inapp"


class NotificationStatus(enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    READ = "read"


# System notification
# ----------------------------------------------------------------------------------------------------------------------


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    type: Mapped[NotificationType] = mapped_column(Enum(NotificationType))
    data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    deliveries: Mapped[list["NotificationDelivery"]] = relationship(
        back_populates="notification", passive_deletes=True, lazy="noload"
    )
    user: Mapped["User"] = relationship(back_populates="notifications", lazy="noload")


# Delivery of a notification via a channel
# ----------------------------------------------------------------------------------------------------------------------


class NotificationDelivery(Base):
    __tablename__ = "notification_delivery"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    notification_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("notifications.id", ondelete="CASCADE"))
    channel: Mapped[NotificationChannel] = mapped_column(Enum(NotificationChannel))

    recipient: Mapped[str] = mapped_column(String)
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    body: Mapped[str] = mapped_column(String)

    status: Mapped[NotificationStatus] = mapped_column(Enum(NotificationStatus), default=NotificationStatus.PENDING)
    failure_message: Mapped[str | None] = mapped_column(String, nullable=True)
    provider_ref: Mapped[str | None] = mapped_column(String, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    notification: Mapped["Notification"] = relationship(back_populates="deliveries", lazy="noload")
