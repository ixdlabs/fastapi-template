import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.notifications.models.notification_delivery import NotificationChannel, NotificationStatus
from app.fixtures.notification_delivery_factory import NotificationDeliveryFactory
from app.fixtures.notification_factory import NotificationFactory
from app.fixtures.user_factory import UserFactory

from app.features.users.models.user import User

BASE_URL = "/api/v1/common/notifications"


@pytest.mark.asyncio
async def test_user_can_view_notification_details(
    test_client_fixture: TestClient, db_fixture: AsyncSession, authenticated_user_fixture: User
):
    notification = NotificationFactory.build(user=authenticated_user_fixture, data={"key": "value"})
    db_fixture.add(notification)
    await db_fixture.flush()
    delivery = NotificationDeliveryFactory.build(
        notification=notification, channel=NotificationChannel.INAPP, status=NotificationStatus.SENT
    )
    db_fixture.add(delivery)
    await db_fixture.commit()
    await db_fixture.refresh(delivery)

    response = test_client_fixture.get(f"{BASE_URL}/{delivery.id}")
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == str(delivery.id)
    assert data["notification"]["data"] == {"key": "value"}


@pytest.mark.asyncio
async def test_user_cannot_access_other_users_notification(
    test_client_fixture: TestClient, db_fixture: AsyncSession, authenticated_user_fixture: User
):
    assert authenticated_user_fixture is not None

    other_user: User = UserFactory.build()
    notification = NotificationFactory.build(user=other_user)
    notification_delivery = NotificationDeliveryFactory.build(
        notification=notification, channel=NotificationChannel.INAPP, status=NotificationStatus.SENT
    )
    db_fixture.add(other_user)
    db_fixture.add(notification)
    db_fixture.add(notification_delivery)
    await db_fixture.commit()
    await db_fixture.refresh(notification_delivery)

    response = test_client_fixture.get(f"{BASE_URL}/{notification_delivery.id}")
    assert response.status_code == 404
    assert response.json()["type"] == "notifications/common/detail-notification/notification-not-found"
