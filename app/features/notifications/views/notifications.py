import uuid

from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from typing import Any, Annotated, Literal
from sqlalchemy import select, update, func

from app.config.auth import CurrentUserDep
from app.config.database import DbDep
from app.config.pagination import Page, paginate
from app.features.notifications.models import (
    Notification,
    NotificationDelivery,
    NotificationChannel,
    NotificationStatus,
)


class NotificationListInput(BaseModel):
    limit: int = Field(10, gt=0, le=20)
    offset: int = Field(0, ge=0)
    order_by: Literal["created_at", "updated_at"] = "created_at"


class NotificationListOutput(BaseModel):
    id: uuid.UUID
    title: str | None
    data: dict[str, Any]
    body: str
    status: NotificationStatus
    created_at: datetime


class NotificationOutput(BaseModel):
    id: uuid.UUID
    data: dict[str, Any]

    recipient: str
    title: str | None
    body: str
    status: NotificationStatus

    sent_at: datetime
    read_at: datetime

    created_at: datetime
    updated_at: datetime


class NotificationSummaryOutput(BaseModel):
    unread_count: int


router = APIRouter()

# Notifications GET endpoint (Lists all the In-App notifications of the user)
# ----------------------------------------------------------------------------------------------------------------------


@router.get("/")
async def get_notifications(
    db: DbDep, current_user: CurrentUserDep, query: Annotated[NotificationListInput, Query()]
) -> Page[NotificationListOutput]:
    stmt = (
        select(NotificationDelivery, Notification.data)
        .join(Notification)
        .where(Notification.user_id == current_user.id, NotificationDelivery.channel == NotificationChannel.INAPP)
    )
    order_column = (
        NotificationDelivery.created_at if query.order_by == "created_at" else NotificationDelivery.updated_at
    )
    stmt = stmt.order_by(order_column.desc())
    result = await paginate(db, stmt, query.limit, query.offset)
    return result.map_to(
        lambda row: NotificationListOutput(
            id=row.NotificationDelivery.id,
            title=row.NotificationDelivery.title,
            data=row.data,
            body=row.NotificationDelivery.body,
            status=row.NotificationDelivery.status,
            created_at=row.NotificationDelivery.created_at,
        )
    )


# Notifications Summary GET endpoint (Return the count of unread In-App notifications)
# ----------------------------------------------------------------------------------------------------------------------


@router.get("/summary")
async def count_unread_notifications(db: DbDep, current_user: CurrentUserDep) -> NotificationSummaryOutput:
    stmt = (
        select(func.count())
        .select_from(NotificationDelivery)
        .join(NotificationDelivery)
        .where(
            Notification.user_id == current_user.id,
            NotificationDelivery.channel == NotificationChannel.INAPP,
            NotificationDelivery.status == NotificationStatus.SENT,
        )
    )
    count = await db.scalar(stmt) or 0
    return NotificationSummaryOutput(unread_count=count)


# Read All Notifications POST endpoint (Read all notifications)
# ----------------------------------------------------------------------------------------------------------------------


@router.post("/read-all")
async def read_all_notifications(db: DbDep, current_user: CurrentUserDep):
    subquery = (
        select(NotificationDelivery.id)
        .join(Notification)
        .where(
            Notification.user_id == current_user.id,
            NotificationDelivery.channel == NotificationChannel.INAPP,
            NotificationDelivery.status == NotificationStatus.SENT,
        )
    )
    stmt = (
        update(NotificationDelivery)
        .where(NotificationDelivery.id.in_(subquery))
        .values(status=NotificationStatus.READ, read_at=datetime.now(), updated_at=datetime.now())
    )

    await db.execute(stmt)
    await db.commit()


# Notification GET endpoint (Return a specific notification)
# ----------------------------------------------------------------------------------------------------------------------


@router.get("/{notification_id}")
async def get_notification(db: DbDep, current_user: CurrentUserDep, notification_id: uuid.UUID):
    stmt = (
        select(NotificationDelivery, Notification.data)
        .join(Notification)
        .where(
            NotificationDelivery.id == notification_id,
            Notification.user_id == current_user.id,
            NotificationDelivery.channel == NotificationChannel.INAPP,
        )
    )

    result = await db.execute(stmt)
    notification = result.first()

    if notification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

    notification_delivery = notification.NotificationDelivery
    notification_data = notification.data

    return NotificationOutput(
        id=notification_delivery.id,
        data=notification_data,
        recipient=notification_delivery.recipient,
        title=notification_delivery.title,
        body=notification_delivery.body,
        status=notification_delivery.status,
        sent_at=notification_delivery.sent_at,
        read_at=notification_delivery.read_at,
        created_at=notification_delivery.created_at,
        updated_at=notification_delivery.updated_at,
    )


# Read Notification POST endpoint (Read a specific notification)
# ----------------------------------------------------------------------------------------------------------------------


@router.post("/{notification_id}/read")
async def read_notification(db: DbDep, current_user: CurrentUserDep, notification_id: uuid.UUID):
    stmt = (
        select(NotificationDelivery)
        .join(Notification)
        .where(NotificationDelivery.id == notification_id, Notification.user_id == current_user.id)
    )

    result = await db.execute(stmt)
    notification = result.scalar_one_or_none()

    if notification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    elif notification.status == NotificationStatus.READ:
        return
    else:
        notification.status = NotificationStatus.READ
        notification.read_at = datetime.now()
        notification.updated_at = datetime.now()

        await db.commit()


# Unread Notification POST endpoint (Unread a specific notification)
# ----------------------------------------------------------------------------------------------------------------------


@router.post("/{notification_id}/unread")
async def unread_notification(db: DbDep, current_user: CurrentUserDep, notification_id: uuid.UUID):
    stmt = (
        select(NotificationDelivery)
        .join(Notification)
        .where(NotificationDelivery.id == notification_id, Notification.user_id == current_user.id)
    )

    result = await db.execute(stmt)
    notification = result.scalar_one_or_none()

    if notification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    elif notification.status == NotificationStatus.SENT:
        return
    else:
        notification.status = NotificationStatus.SENT
        notification.read_at = None
        notification.updated_at = datetime.now()

        await db.commit()
