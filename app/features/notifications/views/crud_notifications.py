import uuid

from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from typing import Any, Annotated, Literal
from sqlalchemy.orm import joinedload
from sqlalchemy import select

from app.config.auth import CurrentUserDep
from app.config.database import DbDep
from app.config.exceptions import raises
from app.config.pagination import Page, paginate
from app.features.notifications.models import (
    Notification,
    NotificationDelivery,
    NotificationChannel,
    NotificationStatus,
    NotificationType,
)


class NotificationListInput(BaseModel):
    limit: int = Field(10, gt=0, le=20)
    offset: int = Field(0, ge=0)
    order_by: Literal["created_at", "updated_at"] = "created_at"


class NotificationDeliveryOutputNotification(BaseModel):
    type: NotificationType
    data: dict[str, Any]


class NotificationDeliveryOutput(BaseModel):
    id: uuid.UUID
    recipient: str
    title: str | None
    body: str
    status: NotificationStatus
    sent_at: datetime | None
    read_at: datetime | None
    created_at: datetime | None
    updated_at: datetime | None
    notification: NotificationDeliveryOutputNotification


class NotificationSummaryOutput(BaseModel):
    unread_count: int


router = APIRouter()

# Notifications GET endpoint
# ----------------------------------------------------------------------------------------------------------------------


@router.get("/")
async def get_notifications(
    query: Annotated[NotificationListInput, Query()], current_user: CurrentUserDep, db: DbDep
) -> Page[NotificationDeliveryOutput]:
    """Lists all the In-App, sent notifications of the user"""
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


# Notification GET endpoint
# ----------------------------------------------------------------------------------------------------------------------


@raises(status.HTTP_404_NOT_FOUND, "Notification not found")
@router.get("/{notification_id}")
async def get_notification(notification_id: uuid.UUID, current_user: CurrentUserDep, db: DbDep):
    """Return a specific notification"""
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

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
