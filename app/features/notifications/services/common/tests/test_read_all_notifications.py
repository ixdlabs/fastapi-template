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

from app.features.users.models.user import User

URL = "/api/v1/common/notifications/read-all"


@pytest.mark.asyncio
async def test_user_can_read_all_notifications(
    test_client_fixture: TestClient, db_fixture: AsyncSession, authenticated_user_fixture: User
):
    notification = NotificationFactory.build(user=authenticated_user_fixture)
    d1: NotificationDelivery = NotificationDeliveryFactory.build(
        notification=notification, channel=NotificationChannel.INAPP, status=NotificationStatus.SENT
    )
    d2: NotificationDelivery = NotificationDeliveryFactory.build(
        notification=notification, channel=NotificationChannel.INAPP, status=NotificationStatus.SENT
    )
    db_fixture.add(notification)
    db_fixture.add_all([d1, d2])
    await db_fixture.commit()

    response = test_client_fixture.post(URL)
    assert response.status_code == 200

    await db_fixture.refresh(d1)
    await db_fixture.refresh(d2)
    assert d1.read_at is not None
    assert d2.read_at is not None
