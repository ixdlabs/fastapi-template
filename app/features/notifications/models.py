from datetime import datetime
import uuid
from enum import Enum
from sqlalchemy.types import SAEnum

from app.config.database import Base
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy import UUID, String, DateTime, JSON, ForeignKey
from typing import Dict, Any, Optional


class NotificationType(Enum):
    CUSTOM = "custom"
    WELCOME = "welcome"


class NotificationChannel(Enum):
    EMAIL = "email"
    SMS = "sms"
    INAPP = "inapp"


class NotificationStatus(Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    type: Mapped[NotificationType] = mapped_column(SAEnum(NotificationType))
    data: Mapped[Dict[str, Any]] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


class NotificationDelivery(Base):
    __tablename__ = "notification_delivery"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    notification_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("notifications.id", ondelete="CASCADE"))
    channel: Mapped[NotificationChannel] = mapped_column(SAEnum(NotificationChannel))
    receipant: Mapped[str] = mapped_column(String)
    title: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    body: Mapped[str] = mapped_column(String)
    status: Mapped[NotificationStatus] = mapped_column(SAEnum(NotificationStatus))
    failure_error_message: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    provider_message_ref: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
