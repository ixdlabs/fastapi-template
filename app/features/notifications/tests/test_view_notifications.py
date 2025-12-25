import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app

from app.features.users.models import User
from app.features.users.tests.fixtures import UserFactory
from app.features.notifications.models import NotificationChannel, NotificationStatus
from app.features.notifications.tests.fixtures import NotificationFactory, NotificationDeliveryFactory


client = TestClient(app)


@pytest.mark.asyncio
async def test_get_notifications_list_returns_correct_data(db_fixture: AsyncSession, logged_in_user_fixture: User):
    current_user = logged_in_user_fixture
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
async def test_get_summary_counts_only_unread_inapp(db_fixture: AsyncSession, logged_in_user_fixture: User):
    current_user = logged_in_user_fixture

    notification = NotificationFactory.build(user=current_user)
    db_fixture.add(notification)
    await db_fixture.flush()

    unread = NotificationDeliveryFactory.build(
        notification=notification, channel=NotificationChannel.INAPP, status=NotificationStatus.SENT, read_at=None
    )
    db_fixture.add(unread)

    read_notification = NotificationDeliveryFactory.build(
        notification=notification,
        channel=NotificationChannel.INAPP,
        status=NotificationStatus.SENT,
        read_at=datetime.now(),
    )
    db_fixture.add(read_notification)

    await db_fixture.commit()

    response = client.get("/api/v1/notifications/summary")

    assert response.status_code == 200
    assert response.json() == {"unread_count": 1}


@pytest.mark.asyncio
async def test_read_all_updates_status(db_fixture: AsyncSession, logged_in_user_fixture: User):
    current_user = logged_in_user_fixture

    notification = NotificationFactory.build(user=current_user)
    db_fixture.add(notification)
    await db_fixture.flush()

    d1 = NotificationDeliveryFactory.build(
        notification=notification, channel=NotificationChannel.INAPP, status=NotificationStatus.SENT
    )
    d2 = NotificationDeliveryFactory.build(
        notification=notification, channel=NotificationChannel.INAPP, status=NotificationStatus.SENT
    )
    db_fixture.add_all([d1, d2])
    await db_fixture.commit()

    response = client.post("/api/v1/notifications/read-all")
    assert response.status_code == 200

    await db_fixture.refresh(d1)
    await db_fixture.refresh(d2)
    assert d1.read_at is not None
    assert d2.read_at is not None


@pytest.mark.asyncio
async def test_get_specific_notification_details(db_fixture: AsyncSession, logged_in_user_fixture: User):
    current_user = logged_in_user_fixture

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


@pytest.mark.asyncio
async def test_cannot_access_other_users_notification(db_fixture: AsyncSession, logged_in_user_fixture: User):
    other_user: User = UserFactory.build()
    db_fixture.add(other_user)
    await db_fixture.commit()

    notification = NotificationFactory.build(user=other_user)
    db_fixture.add(notification)
    await db_fixture.flush()

    notification_delivery = NotificationDeliveryFactory.build(
        notification=notification, channel=NotificationChannel.INAPP, status=NotificationStatus.SENT
    )
    db_fixture.add(notification_delivery)
    await db_fixture.commit()
    await db_fixture.refresh(notification_delivery)

    response = client.get(f"/api/v1/notifications/{notification_delivery.id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Notification not found"


@pytest.mark.asyncio
async def test_mark_single_notification_as_read(db_fixture: AsyncSession, logged_in_user_fixture: User):
    current_user = logged_in_user_fixture

    notification = NotificationFactory.build(user=current_user)
    db_fixture.add(notification)
    await db_fixture.flush()

    notification_delivery = NotificationDeliveryFactory.build(
        notification=notification, channel=NotificationChannel.INAPP, status=NotificationStatus.SENT
    )
    db_fixture.add(notification_delivery)
    await db_fixture.commit()
    await db_fixture.refresh(notification_delivery)

    response = client.post(f"/api/v1/notifications/{notification_delivery.id}/read")
    assert response.status_code == 200

    await db_fixture.refresh(notification_delivery)
    assert notification_delivery.read_at is not None


@pytest.mark.asyncio
async def test_mark_single_notification_as_unread(db_fixture: AsyncSession, logged_in_user_fixture: User):
    current_user = logged_in_user_fixture

    notification = NotificationFactory.build(user=current_user)
    db_fixture.add(notification)
    await db_fixture.flush()

    notification_delivery = NotificationDeliveryFactory.build(
        notification=notification, channel=NotificationChannel.INAPP
    )
    db_fixture.add(notification_delivery)
    await db_fixture.commit()
    await db_fixture.refresh(notification_delivery)

    response = client.post(f"/api/v1/notifications/{notification_delivery.id}/unread")
    assert response.status_code == 200

    await db_fixture.refresh(notification_delivery)
    assert notification_delivery.status == NotificationStatus.SENT
    assert notification_delivery.read_at is None
