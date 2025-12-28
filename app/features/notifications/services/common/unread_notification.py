import uuid

from fastapi import APIRouter, status
from pydantic import BaseModel
from sqlalchemy import select

from app.core.auth import AuthenticationFailedException, CurrentUserDep
from app.core.database import DbDep
from app.core.exceptions import ServiceException, raises
from app.features.notifications.models.notification import Notification
from app.features.notifications.models.notification_delivery import NotificationDelivery, NotificationStatus


router = APIRouter()

# Input/Output
# ----------------------------------------------------------------------------------------------------------------------


class UnreadNotificationOutput(BaseModel):
    detail: str = "Notification marked as unread"


# Exceptions
# ----------------------------------------------------------------------------------------------------------------------


class NotificationNotFoundException(ServiceException):
    status_code = status.HTTP_404_NOT_FOUND
    type = "notifications/common/read-notification/notification-not-found"
    detail = "Notification not found, it may have been deleted"


# Unread Notification
# ----------------------------------------------------------------------------------------------------------------------


@raises(NotificationNotFoundException)
@raises(AuthenticationFailedException)
@router.post("/{notification_id}/unread")
async def unread_notification(
    notification_id: uuid.UUID, current_user: CurrentUserDep, db: DbDep
) -> UnreadNotificationOutput:
    """
    Mark a specific sent notification as unread for the current user.
    """
    stmt = (
        select(NotificationDelivery)
        .join(Notification)
        .where(NotificationDelivery.id == notification_id)
        .where(Notification.user_id == current_user.id)
        .where(NotificationDelivery.status == NotificationStatus.SENT)
    )
    result = await db.execute(stmt)
    notification = result.scalar_one_or_none()
    if notification is None:
        raise NotificationNotFoundException()
    if notification.read_at is None:
        return UnreadNotificationOutput()

    notification.read_at = None
    await db.commit()
    return UnreadNotificationOutput()
