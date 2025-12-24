from datetime import datetime
from typing import Any
import uuid
from pydantic import BaseModel
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from app.config.pagination import paginate
from app.features.notifications.models import (
    Notification,
    NotificationChannel,
    NotificationDelivery,
    NotificationStatus,
    NotificationType,
)
from app.features.users.models import User
from app.features.users.tests.fixtures import UserFactory


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


@pytest.mark.asyncio
async def test_test(db_fixture: AsyncSession):
    user: User = UserFactory.build(password__raw="securepassword123", id=uuid.uuid4())
    notification = Notification(
        user_id=user.id,
        type=NotificationType.CUSTOM,
        data={"title": "Test Notification", "message": "This is a test notification."},
    )
    notification_delivery = NotificationDelivery(
        notification=notification,
        channel=NotificationChannel.INAPP,
        recipient="user_inapp_id",
        title="Test Notification Delivery",
        body="This is a test notification delivery.",
        status=NotificationStatus.SENT,
    )
    db_fixture.add(user)
    db_fixture.add(notification)
    db_fixture.add(notification_delivery)
    await db_fixture.commit()
    await db_fixture.refresh(user)
    await db_fixture.refresh(notification)
    await db_fixture.refresh(notification_delivery)

    stmt = (
        select(NotificationDelivery)
        .join(Notification)
        .options(joinedload(NotificationDelivery.notification))
        .where(
            Notification.user_id == user.id,
            NotificationDelivery.channel == NotificationChannel.INAPP,
            NotificationDelivery.status == NotificationStatus.SENT,
        )
    )

    result = await paginate(db_fixture, stmt, limit=10, offset=0)
    response = result.map_to(
        lambda notification_delivery: NotificationOutput(
            id=notification_delivery.id,
            recipient=notification_delivery.recipient,
            title=notification_delivery.title,
            body=notification_delivery.body,
            status=notification_delivery.status,
            sent_at=notification_delivery.sent_at,
            read_at=notification_delivery.read_at,
            created_at=notification_delivery.created_at,
            updated_at=notification_delivery.updated_at,
            type=notification_delivery.notification.type,
            data=notification_delivery.notification.data,
        )
    )
    assert response.count == 1
    assert response.items[0].id == notification_delivery.id
