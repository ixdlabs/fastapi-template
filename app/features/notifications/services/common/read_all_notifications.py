from datetime import datetime, timezone
from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import update

from app.core.auth import AuthenticationFailedException, CurrentUserDep
from app.core.database import DbDep
from app.core.exceptions import raises
from app.features.notifications.models.notification import Notification
from app.features.notifications.models.notification_delivery import (
    NotificationDelivery,
    NotificationChannel,
    NotificationStatus,
)


router = APIRouter()

# Input/Output
# ----------------------------------------------------------------------------------------------------------------------


class ReadAllNotificationsOutput(BaseModel):
    detail: str = "All In-App notifications marked as read"


# Read All Notifications
# ----------------------------------------------------------------------------------------------------------------------


@raises(AuthenticationFailedException)
@router.post("/read-all")
async def read_all_notifications(current_user: CurrentUserDep, db: DbDep) -> ReadAllNotificationsOutput:
    """
    Read all sent In-App notifications for the current user.
    """
    stmt = (
        update(NotificationDelivery)
        .where(NotificationDelivery.notification_id == Notification.id)
        .where(Notification.user_id == current_user.id)
        .where(NotificationDelivery.channel == NotificationChannel.INAPP)
        .where(NotificationDelivery.status == NotificationStatus.SENT)
        .where(NotificationDelivery.read_at.is_(None))
        .values(read_at=datetime.now(timezone.utc))
    )
    _ = await db.execute(stmt)
    await db.commit()
    return ReadAllNotificationsOutput()
