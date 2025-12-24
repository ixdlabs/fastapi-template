import uuid

from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from typing import Any, Annotated, Literal
from sqlalchemy.orm import joinedload
from sqlalchemy import select, update, func

from app.config.auth import CurrentUserDep
from app.config.database import DbDep
from app.config.pagination import Page, paginate  # noqa: F401
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


class NotificationOutput(BaseModel):
    id: uuid.UUID
    recipient: str
    title: str | None
    body: str
    status: NotificationStatus
    sent_at: datetime | None
    read_at: datetime | None
    created_at: datetime | None
    updated_at: datetime | None
    type: NotificationType
    data: dict[str, Any]


class NotificationSummaryOutput(BaseModel):
    unread_count: int


router = APIRouter()

# Notifications GET endpoint
# ----------------------------------------------------------------------------------------------------------------------


@router.get("/")
async def get_notifications(
    query: Annotated[NotificationListInput, Query()], current_user: CurrentUserDep, db: DbDep
) -> Page[NotificationOutput]:
    """Lists all the In-App, SENT notifications of the user"""
    stmt = (
        select(NotificationDelivery)
        .join(Notification)
        .options(joinedload(NotificationDelivery.notification))
        .where(
            Notification.user_id == current_user.id,
            NotificationDelivery.channel == NotificationChannel.INAPP,
            NotificationDelivery.status == NotificationStatus.SENT,
        )
    )

    order_column = (
        NotificationDelivery.created_at if query.order_by == "created_at" else NotificationDelivery.updated_at
    )

    stmt = stmt.order_by(order_column)
    result = await paginate(db, stmt, limit=query.limit, offset=query.offset)

    response = result.map_to(
        lambda notification: NotificationOutput(
            id=notification.id,
            recipient=notification.recipient,
            title=notification.title,
            body=notification.body,
            status=notification.status,
            sent_at=notification.sent_at,
            read_at=notification.read_at,
            created_at=notification.created_at,
            updated_at=notification.updated_at,
            type=notification.notification.type,
            data=notification.notification.data,
        )
    )

    return response


# Notifications Summary GET endpoint
# ----------------------------------------------------------------------------------------------------------------------


@router.get("/summary")
async def count_unread_notifications(current_user: CurrentUserDep, db: DbDep) -> NotificationSummaryOutput:
    """Return the count of unread In-App, SENT notifications"""
    stmt = (
        select(func.count())
        .select_from(NotificationDelivery)
        .join(Notification)
        .where(
            Notification.user_id == current_user.id,
            NotificationDelivery.channel == NotificationChannel.INAPP,
            NotificationDelivery.status == NotificationStatus.SENT,
            NotificationDelivery.read_at.is_(None),
        )
    )
    count = await db.scalar(stmt) or 0
    return NotificationSummaryOutput(unread_count=count)


# Read All Notifications POST endpoint
# ----------------------------------------------------------------------------------------------------------------------


@router.post("/read-all")
async def read_all_notifications(current_user: CurrentUserDep, db: DbDep):
    """Read all SENT notifications"""
    subquery = (
        select(NotificationDelivery.id)
        .join(Notification)
        .where(
            Notification.user_id == current_user.id,
            NotificationDelivery.channel == NotificationChannel.INAPP,
            NotificationDelivery.status == NotificationStatus.SENT,
            NotificationDelivery.read_at.is_(None),
        )
    )
    stmt = update(NotificationDelivery).where(NotificationDelivery.id.in_(subquery)).values(read_at=datetime.now())

    await db.execute(stmt)
    await db.commit()


# Notification GET endpoint
# ----------------------------------------------------------------------------------------------------------------------


@router.get("/{notification_id}")
async def get_notification(notification_id: uuid.UUID, current_user: CurrentUserDep, db: DbDep):
    """Return a specific notification"""
    stmt = (
        select(NotificationDelivery)
        .join(Notification)
        .options(joinedload(NotificationDelivery.notification))
        .where(
            Notification.user_id == current_user.id,
            NotificationDelivery.channel == NotificationChannel.INAPP,
            NotificationDelivery.status == NotificationStatus.SENT,
        )
    )

    result = await db.execute(stmt)
    notification = result.scalars().first()

    if notification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

    return NotificationOutput(
        id=notification.id,
        recipient=notification.recipient,
        title=notification.title,
        body=notification.body,
        status=notification.status,
        sent_at=notification.sent_at,
        read_at=notification.read_at,
        created_at=notification.created_at,
        updated_at=notification.updated_at,
        type=notification.notification.type,
        data=notification.notification.data,
    )


# Read Notification POST endpoint
# ----------------------------------------------------------------------------------------------------------------------


@router.post("/{notification_id}/read")
async def read_notification(notification_id: uuid.UUID, current_user: CurrentUserDep, db: DbDep):
    """Read a specific SENT notification"""
    stmt = (
        select(NotificationDelivery)
        .join(Notification)
        .where(NotificationDelivery.id == notification_id, Notification.user_id == current_user.id)
    )

    result = await db.execute(stmt)
    notification = result.scalar_one_or_none()

    if notification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

    if notification.status == NotificationStatus.SENT and notification.read_at is not None:
        return

    notification.read_at = datetime.now()

    await db.commit()


# Unread Notification POST endpoint
# ----------------------------------------------------------------------------------------------------------------------


@router.post("/{notification_id}/unread")
async def unread_notification(notification_id: uuid.UUID, current_user: CurrentUserDep, db: DbDep):
    """Unread a specific SENT notification"""
    stmt = (
        select(NotificationDelivery)
        .join(Notification)
        .where(NotificationDelivery.id == notification_id, Notification.user_id == current_user.id)
    )

    result = await db.execute(stmt)
    notification = result.scalar_one_or_none()

    if notification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

    if notification.status == NotificationStatus.SENT and notification.read_at is None:
        return

    notification.read_at = None

    await db.commit()
