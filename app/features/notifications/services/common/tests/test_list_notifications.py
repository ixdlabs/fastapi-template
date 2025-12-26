import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.notifications.models.notification_delivery import NotificationChannel, NotificationStatus
from app.fixtures.notification_delivery_factory import NotificationDeliveryFactory
from app.fixtures.notification_factory import NotificationFactory
from app.main import app

from app.features.users.models.user import User

client = TestClient(app)
url = "/api/v1/common/notifications"


@pytest.mark.asyncio
async def test_user_can_list_notifications(db_fixture: AsyncSession, authenticated_user_fixture: User):
    notification = NotificationFactory.build(user=authenticated_user_fixture)
    db_fixture.add(notification)
    await db_fixture.flush()
    notification_delivery = NotificationDeliveryFactory.build(
        notification=notification, channel=NotificationChannel.INAPP, status=NotificationStatus.SENT
    )
    email_delivery = NotificationDeliveryFactory.build(
        notification=notification, channel=NotificationChannel.EMAIL, status=NotificationStatus.SENT
    )
    db_fixture.add(notification_delivery)
    db_fixture.add(email_delivery)
    await db_fixture.commit()
    await db_fixture.refresh(notification_delivery)

    response = client.get(url)
    assert response.status_code == 200

    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["id"] == str(notification_delivery.id)
    assert data["items"][0]["status"] == NotificationStatus.SENT.value
