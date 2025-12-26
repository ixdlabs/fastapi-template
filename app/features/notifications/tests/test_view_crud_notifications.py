import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app

from app.features.users.models.user import User
from app.features.notifications.models import NotificationChannel, NotificationStatus
from app.features.notifications.tests.fixtures import NotificationFactory, NotificationDeliveryFactory

client = TestClient(app)


@pytest.mark.asyncio
async def test_get_notifications_list_returns_correct_data(db_fixture: AsyncSession, authenticated_user_fixture: User):
    current_user = authenticated_user_fixture
    notification = NotificationFactory.build(user=current_user)
    db_fixture.add(notification)
    await db_fixture.flush()

    notification_delivery = NotificationDeliveryFactory.build(
        notification=notification, channel=NotificationChannel.INAPP, status=NotificationStatus.SENT
    )
    db_fixture.add(notification_delivery)

    email_delivery = NotificationDeliveryFactory.build(
        notification=notification, channel=NotificationChannel.EMAIL, status=NotificationStatus.SENT
    )
    db_fixture.add(email_delivery)

    await db_fixture.commit()
    await db_fixture.refresh(notification_delivery)

    response = client.get("api/v1/notifications")

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["id"] == str(notification_delivery.id)
    assert data["items"][0]["status"] == NotificationStatus.SENT.value


@pytest.mark.asyncio
async def test_get_specific_notification_details(db_fixture: AsyncSession, authenticated_user_fixture: User):
    current_user = authenticated_user_fixture

    notification = NotificationFactory.build(user=current_user, data={"key": "value"})
    db_fixture.add(notification)
    await db_fixture.flush()

    delivery = NotificationDeliveryFactory.build(
        notification=notification, channel=NotificationChannel.INAPP, status=NotificationStatus.SENT
    )
    db_fixture.add(delivery)
    await db_fixture.commit()
    await db_fixture.refresh(delivery)

    response = client.get(f"/api/v1/notifications/{delivery.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(delivery.id)
    assert data["notification"]["data"] == {"key": "value"}
