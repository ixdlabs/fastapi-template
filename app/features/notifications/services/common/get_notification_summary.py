from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select, func

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


class GetNotificationSummaryOutput(BaseModel):
    unread_count: int


# Notifications Summary
# ----------------------------------------------------------------------------------------------------------------------


@raises(AuthenticationFailedException)
@router.get("/summary")
async def get_notification_summary(current_user: CurrentUserDep, db: DbDep) -> GetNotificationSummaryOutput:
    """
    Return a summary of notifications for the current user.
    Currently, it provides the count of sent but unread In-App notifications.
    """
    stmt = (
        select(func.count())
        .select_from(NotificationDelivery)
        .join(Notification)
        .where(Notification.user_id == current_user.id)
        .where(NotificationDelivery.channel == NotificationChannel.INAPP)
        .where(NotificationDelivery.status == NotificationStatus.SENT)
        .where(NotificationDelivery.read_at.is_(None))
    )
    count = await db.scalar(stmt) or 0

    return GetNotificationSummaryOutput(unread_count=count)
