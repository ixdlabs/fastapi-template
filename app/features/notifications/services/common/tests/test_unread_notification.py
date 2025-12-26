from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.notifications.models.notification_delivery import (
    NotificationChannel,
    NotificationDelivery,
    NotificationStatus,
)
from app.fixtures.notification_delivery_factory import NotificationDeliveryFactory
from app.fixtures.notification_factory import NotificationFactory
from app.main import app

from app.features.users.models.user import User

client = TestClient(app)
base_url = "/api/v1/common/notifications"


@pytest.mark.asyncio
async def test_user_can_mark_notification_as_unread(db_fixture: AsyncSession, authenticated_user_fixture: User):
    notification = NotificationFactory.build(user=authenticated_user_fixture)
    notification_delivery: NotificationDelivery = NotificationDeliveryFactory.build(
        notification=notification,
        channel=NotificationChannel.INAPP,
        status=NotificationStatus.SENT,
        read_at=datetime.now(timezone.utc),
    )
    db_fixture.add(notification)
    db_fixture.add(notification_delivery)
    await db_fixture.commit()
    await db_fixture.refresh(notification_delivery)

    response = client.post(f"{base_url}/{notification_delivery.id}/unread")
    assert response.status_code == 200

    await db_fixture.refresh(notification_delivery)
    assert notification_delivery.read_at is None
