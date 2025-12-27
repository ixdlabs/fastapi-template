from typing import Annotated, Literal
import uuid

from fastapi import APIRouter, Query
from pydantic import AwareDatetime, BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.config.auth import AuthenticationFailedException, CurrentUserDep
from app.config.database import DbDep
from app.config.exceptions import raises
from app.config.pagination import Page, paginate
from app.features.notifications.models.notification import Notification, NotificationType
from app.features.notifications.models.notification_delivery import (
    NotificationChannel,
    NotificationDelivery,
    NotificationStatus,
)


router = APIRouter()

# Input/Output
# ----------------------------------------------------------------------------------------------------------------------


class NotificationListInput(BaseModel):
    limit: int = Field(10, gt=0, le=20)
    offset: int = Field(0, ge=0)
    order_by: Literal["created_at", "updated_at"] = "created_at"


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


# List My Notifications
# ----------------------------------------------------------------------------------------------------------------------


@raises(AuthenticationFailedException)
@router.get("/")
async def list_notifications(
    query: Annotated[NotificationListInput, Query()], current_user: CurrentUserDep, db: DbDep
) -> Page[NotificationDeliveryOutput]:
    """List In-App notifications for the current user."""
    stmt = (
        select(NotificationDelivery)
        .join(Notification)
        .options(joinedload(NotificationDelivery.notification))
        .where(Notification.user_id == current_user.id)
        .where(NotificationDelivery.channel == NotificationChannel.INAPP)
        .where(NotificationDelivery.status == NotificationStatus.SENT)
    )
    order_column = (
        NotificationDelivery.created_at if query.order_by == "created_at" else NotificationDelivery.updated_at
    )
    stmt = stmt.order_by(order_column)
    result = await paginate(db, stmt, limit=query.limit, offset=query.offset)

    return result.map_to(
        lambda notification: NotificationDeliveryOutput(
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
    )
