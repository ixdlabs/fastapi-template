from datetime import datetime
import uuid
import enum
import typing

from app.core.database import Base

from sqlalchemy.types import Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import UUID, JSON, ForeignKey

from app.core.timezone import DateTimeUTC, utc_now

if typing.TYPE_CHECKING:
    from app.features.users.models.user import User
    from app.features.notifications.models.notification_delivery import NotificationDelivery


# System notification
# This only represents the notification intent, the actual delivery records are in NotificationDelivery.
# ----------------------------------------------------------------------------------------------------------------------


class NotificationType(enum.Enum):
    WELCOME = "welcome"


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    type: Mapped[NotificationType] = mapped_column(Enum(NotificationType))
    data: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTimeUTC, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTimeUTC, default=utc_now, onupdate=utc_now)

    deliveries: Mapped[list["NotificationDelivery"]] = relationship(
        back_populates="notification", passive_deletes=True, lazy="raise_on_sql"
    )
    user: Mapped["User"] = relationship(back_populates="notifications", lazy="raise_on_sql")
