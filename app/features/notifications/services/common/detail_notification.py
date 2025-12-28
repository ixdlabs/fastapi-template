import uuid

from fastapi import APIRouter, status
from pydantic import AwareDatetime, BaseModel
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.core.auth import AuthenticationFailedException, CurrentUserDep
from app.core.database import DbDep
from app.core.exceptions import ServiceException, raises
from app.features.notifications.models.notification import Notification, NotificationType
from app.features.notifications.models.notification_delivery import (
    NotificationChannel,
    NotificationDelivery,
    NotificationStatus,
)


router = APIRouter()

# Input/Output
# ----------------------------------------------------------------------------------------------------------------------


class NotificationDeliveryOutputNotification(BaseModel):
    type: NotificationType
    data: dict[str, object]


class NotificationDeliveryOutput(BaseModel):
    id: uuid.UUID
    recipient: str
    title: str | None
    body: str
    status: NotificationStatus
    sent_at: AwareDatetime | None
    read_at: AwareDatetime | None
    created_at: AwareDatetime | None
    updated_at: AwareDatetime | None
    notification: NotificationDeliveryOutputNotification


# Exceptions
# ----------------------------------------------------------------------------------------------------------------------


class NotificationNotFoundException(ServiceException):
    status_code = status.HTTP_404_NOT_FOUND
    type = "notifications/common/detail-notification/notification-not-found"
    detail = "Notification not found, it may have been deleted"


# Detail Notification
# ----------------------------------------------------------------------------------------------------------------------


@raises(NotificationNotFoundException)
@raises(AuthenticationFailedException)
@router.get("/{notification_id}")
async def detail_notification(notification_id: uuid.UUID, current_user: CurrentUserDep, db: DbDep):
    """Retrieve a specific sent In-App notification belonging to the current user."""
    stmt = (
        select(NotificationDelivery)
        .join(Notification)
        .options(joinedload(NotificationDelivery.notification))
        .where(NotificationDelivery.id == notification_id)
        .where(Notification.user_id == current_user.id)
        .where(NotificationDelivery.channel == NotificationChannel.INAPP)
        .where(NotificationDelivery.status == NotificationStatus.SENT)
    )
    result = await db.execute(stmt)
    notification = result.scalars().first()

    if notification is None:
        raise NotificationNotFoundException()

    return NotificationDeliveryOutput(
        id=notification.id,
        recipient=notification.recipient,
        title=notification.title,
        body=notification.body,
        status=notification.status,
        sent_at=notification.sent_at,
        read_at=notification.read_at,
        created_at=notification.created_at,
        updated_at=notification.updated_at,
        notification=NotificationDeliveryOutputNotification(
            type=notification.notification.type,
            data=notification.notification.data,
        ),
    )
