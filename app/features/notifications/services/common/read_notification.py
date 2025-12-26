import uuid

from datetime import datetime, timezone
from fastapi import APIRouter, status
from pydantic import BaseModel
from sqlalchemy import select

from app.config.auth import AuthenticationFailedException, CurrentUserDep
from app.config.database import DbDep
from app.config.exceptions import ServiceException, raises
from app.features.notifications.models.notification import Notification
from app.features.notifications.models.notification_delivery import NotificationDelivery, NotificationStatus


router = APIRouter()

# Input/Output
# ----------------------------------------------------------------------------------------------------------------------


class ReadNotificationOutput(BaseModel):
    detail: str = "Notification marked as read"


# Exceptions
# ----------------------------------------------------------------------------------------------------------------------


class NotificationNotFoundException(ServiceException):
    status_code = status.HTTP_404_NOT_FOUND
    type = "notifications/common/read-notification/notification-not-found"
    detail = "Notification not found, it may have been deleted"


# Read Notification
# ----------------------------------------------------------------------------------------------------------------------


@raises(NotificationNotFoundException)
@raises(AuthenticationFailedException)
@router.post("/{notification_id}/read")
async def read_notification(
    notification_id: uuid.UUID, current_user: CurrentUserDep, db: DbDep
) -> ReadNotificationOutput:
    """
    Read a specific sent notification belonging to the current user.
    """
    stmt = (
        select(NotificationDelivery)
        .join(Notification)
        .where(NotificationDelivery.id == notification_id)
        .where(NotificationDelivery.status == NotificationStatus.SENT)
        .where(Notification.user_id == current_user.id)
    )
    result = await db.execute(stmt)
    notification = result.scalar_one_or_none()
    if notification is None:
        raise NotificationNotFoundException()
    if notification.read_at is not None:
        return ReadNotificationOutput()

    notification.read_at = datetime.now(timezone.utc)
    await db.commit()
    return ReadNotificationOutput()
