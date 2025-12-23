import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from types import SimpleNamespace

from app.main import app
from app.config.auth import get_current_user
from app.features.users.models import User
from app.features.users.tests.fixtures import UserFactory
from app.features.notifications.models import NotificationChannel, NotificationStatus
from app.features.notifications.tests.fixtures import NotificationFactory, NotificationDeliveryFactory


client = TestClient(app)


async def force_login(user: User, db: AsyncSession):
    await db.refresh(user)

    mock_user = SimpleNamespace(
        id=user.id,
        username=user.username,
    )

    async def mock_get_current_user():
        return mock_user

    app.dependency_overrides[get_current_user] = mock_get_current_user


@pytest.mark.asyncio
async def test_get_notifications_list_returns_correct_data(db_fixture: AsyncSession):
    user: User = UserFactory.build()
    db_fixture.add(user)
    await db_fixture.commit()
    await db_fixture.refresh(user)
    await force_login(user, db_fixture)

    notification = NotificationFactory.build(user=user)
    db_fixture.add(notification)
    await db_fixture.flush()

    delivery = NotificationDeliveryFactory.build(notification=notification, channel=NotificationChannel.INAPP)
    db_fixture.add(delivery)

    email_delivery = NotificationDeliveryFactory.build(notification=notification, channel=NotificationChannel.EMAIL)
    db_fixture.add(email_delivery)

    await db_fixture.commit()
    await db_fixture.refresh(delivery)
    response = client.get("/api/v1/notifications")

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["id"] == str(delivery.id)
    assert data["items"][0]["status"] == NotificationStatus.SENT.value

    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_get_summary_counts_only_unread_inapp(db_fixture: AsyncSession):
    user: User = UserFactory.build()
    db_fixture.add(user)
    await db_fixture.commit()
    await db_fixture.refresh(user)
    await force_login(user, db_fixture)

    notification = NotificationFactory.build(user=user)
    db_fixture.add(notification)
    await db_fixture.flush()

    unread = NotificationDeliveryFactory.build(
        notification=notification, channel=NotificationChannel.INAPP, status=NotificationStatus.SENT
    )
    db_fixture.add(unread)

    read_notif = NotificationDeliveryFactory.build(
        notification=notification, channel=NotificationChannel.INAPP, status=NotificationStatus.READ
    )
    db_fixture.add(read_notif)

    await db_fixture.commit()

    response = client.get("/api/v1/notifications/summary")

    assert response.status_code == 200
    assert response.json() == {"unread_count": 1}
    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_read_all_updates_status(db_fixture: AsyncSession):
    user: User = UserFactory.build()
    db_fixture.add(user)
    await db_fixture.commit()
    await db_fixture.refresh(user)
    await force_login(user, db_fixture)

    notification = NotificationFactory.build(user=user)
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

    # Verify DB
    await db_fixture.refresh(d1)
    await db_fixture.refresh(d2)
    assert d1.status == NotificationStatus.READ
    assert d2.status == NotificationStatus.READ
    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_get_specific_notification_details(db_fixture: AsyncSession):
    user: User = UserFactory.build()
    db_fixture.add(user)
    await db_fixture.commit()
    await db_fixture.refresh(user)
    await force_login(user, db_fixture)

    notification = NotificationFactory.build(user=user, data={"key": "value"})
    db_fixture.add(notification)
    await db_fixture.flush()

    delivery = NotificationDeliveryFactory.build(notification=notification, channel=NotificationChannel.INAPP)
    db_fixture.add(delivery)
    await db_fixture.commit()
    await db_fixture.refresh(delivery)

    response = client.get(f"/api/v1/notifications/{delivery.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(delivery.id)
    assert data["data"] == {"key": "value"}
    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_cannot_access_other_users_notification(db_fixture: AsyncSession):
    user1: User = UserFactory.build()
    db_fixture.add(user1)

    user2: User = UserFactory.build()
    db_fixture.add(user2)
    await db_fixture.commit()

    await force_login(user1, db_fixture)

    notification = NotificationFactory.build(user=user2)
    db_fixture.add(notification)
    await db_fixture.flush()

    delivery = NotificationDeliveryFactory.build(notification=notification, channel=NotificationChannel.INAPP)
    db_fixture.add(delivery)
    await db_fixture.commit()
    await db_fixture.refresh(delivery)

    response = client.get(f"/api/v1/notifications/{delivery.id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Notification not found"
    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_mark_single_notification_as_read(db_fixture: AsyncSession):
    user: User = UserFactory.build()
    db_fixture.add(user)
    await db_fixture.commit()
    await db_fixture.refresh(user)
    await force_login(user, db_fixture)

    notification = NotificationFactory.build(user=user)
    db_fixture.add(notification)
    await db_fixture.flush()

    delivery = NotificationDeliveryFactory.build(
        notification=notification, channel=NotificationChannel.INAPP, status=NotificationStatus.SENT
    )
    db_fixture.add(delivery)
    await db_fixture.commit()
    await db_fixture.refresh(delivery)

    response = client.post(f"/api/v1/notifications/{delivery.id}/read")
    assert response.status_code == 200

    await db_fixture.refresh(delivery)
    assert delivery.status == NotificationStatus.READ
    assert delivery.read_at is not None
    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_mark_single_notification_as_unread(db_fixture: AsyncSession):
    user: User = UserFactory.build()
    db_fixture.add(user)
    await db_fixture.commit()
    await db_fixture.refresh(user)
    await force_login(user, db_fixture)

    notification = NotificationFactory.build(user=user)
    db_fixture.add(notification)
    await db_fixture.flush()

    delivery = NotificationDeliveryFactory.build(
        notification=notification, channel=NotificationChannel.INAPP, status=NotificationStatus.READ
    )
    db_fixture.add(delivery)
    await db_fixture.commit()
    await db_fixture.refresh(delivery)

    response = client.post(f"/api/v1/notifications/{delivery.id}/unread")
    assert response.status_code == 200

    await db_fixture.refresh(delivery)
    assert delivery.status == NotificationStatus.SENT
    assert delivery.read_at is None
    app.dependency_overrides = {}
