import uuid

from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, update, func

from app.config.auth import CurrentUserDep
from app.config.database import DbDep
from app.config.exceptions import raises
from app.features.notifications.models import (
    Notification,
    NotificationDelivery,
    NotificationChannel,
    NotificationStatus,
)


class NotificationSummaryOutput(BaseModel):
    unread_count: int


router = APIRouter()

# Notifications Summary GET endpoint
# ----------------------------------------------------------------------------------------------------------------------


@router.get("/summary")
async def count_unread_notifications(current_user: CurrentUserDep, db: DbDep) -> NotificationSummaryOutput:
    """Return the count of unread In-App, sent notifications"""
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

    return NotificationSummaryOutput(unread_count=count)


# Read All Notifications POST endpoint
# ----------------------------------------------------------------------------------------------------------------------


@router.post("/read-all")
async def read_all_notifications(current_user: CurrentUserDep, db: DbDep):
    """Read all sent notifications"""
    stmt = (
        update(NotificationDelivery)
        .where(NotificationDelivery.notification_id == Notification.id)  # The Join condition
        .where(Notification.user_id == current_user.id)
        .where(NotificationDelivery.channel == NotificationChannel.INAPP)
        .where(NotificationDelivery.status == NotificationStatus.SENT)
        .where(NotificationDelivery.read_at.is_(None))
        .values(read_at=datetime.now(timezone.utc))
    )
    await db.execute(stmt)
    await db.commit()


# Read Notification POST endpoint
# ----------------------------------------------------------------------------------------------------------------------


@raises(status.HTTP_404_NOT_FOUND, "Notification not found")
@router.post("/{notification_id}/read")
async def read_notification(notification_id: uuid.UUID, current_user: CurrentUserDep, db: DbDep):
    """Read a specific sent notification"""
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    if notification.read_at is not None:
        return
    notification.read_at = datetime.now(timezone.utc)
    await db.commit()


# Unread Notification POST endpoint
# ----------------------------------------------------------------------------------------------------------------------


@raises(status.HTTP_404_NOT_FOUND, "Notification not found")
@router.post("/{notification_id}/unread")
async def unread_notification(notification_id: uuid.UUID, current_user: CurrentUserDep, db: DbDep):
    """Unread a specific sent notification"""
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    if notification.read_at is None:
        return
    notification.read_at = None
    await db.commit()
