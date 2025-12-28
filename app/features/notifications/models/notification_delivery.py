from datetime import datetime
import enum
import uuid
import typing

from app.core.database import Base

from sqlalchemy.types import Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import UUID, String, ForeignKey

from app.core.timezone import DateTimeUTC, utc_now

if typing.TYPE_CHECKING:
    from app.features.notifications.models.notification import Notification


# Notification Delivery
# This model represents the delivery of a notification via a specific channel (e.g., email, SMS, in-app).
# This is the actual record that is given to the user.
# In-app notifications are the ones that the user can read via the application interface.
# ----------------------------------------------------------------------------------------------------------------------


class NotificationChannel(enum.Enum):
    EMAIL = "email"
    SMS = "sms"
    INAPP = "inapp"


class NotificationStatus(enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


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
    sent_at: Mapped[datetime | None] = mapped_column(DateTimeUTC, nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTimeUTC, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTimeUTC, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTimeUTC, default=utc_now, onupdate=utc_now)

    notification: Mapped["Notification"] = relationship(back_populates="deliveries", lazy="raise_on_sql")
