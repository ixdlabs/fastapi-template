from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.notifications.models.notification_delivery import NotificationChannel, NotificationStatus
from app.fixtures.notification_delivery_factory import NotificationDeliveryFactory
from app.fixtures.notification_factory import NotificationFactory
from app.main import app

from app.features.users.models.user import User

client = TestClient(app)
url = "/api/v1/common/notifications/summary"


@pytest.mark.asyncio
async def test_user_can_get_notification_summary_containing_only_unread_inapp_notifications(
    db_fixture: AsyncSession, authenticated_user_fixture: User
):
    notification = NotificationFactory.build(user=authenticated_user_fixture)
    unread = NotificationDeliveryFactory.build(
        notification=notification, channel=NotificationChannel.INAPP, status=NotificationStatus.SENT, read_at=None
    )
    read_notification = NotificationDeliveryFactory.build(
        notification=notification,
        channel=NotificationChannel.INAPP,
        status=NotificationStatus.SENT,
        read_at=datetime.now(timezone.utc),
    )
    db_fixture.add(notification)
    db_fixture.add(unread)
    db_fixture.add(read_notification)

    await db_fixture.commit()

    response = client.get(url)
    assert response.status_code == 200
    assert response.json() == {"unread_count": 1}
