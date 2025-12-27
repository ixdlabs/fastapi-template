import factory

from app.features.notifications.models.notification_delivery import (
    NotificationChannel,
    NotificationDelivery,
    NotificationStatus,
)
from app.fixtures.notification_factory import NotificationFactory


class NotificationDeliveryFactory(factory.Factory[NotificationDelivery]):
    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        model = NotificationDelivery

    notification = factory.SubFactory(NotificationFactory)
    channel = factory.Iterator(NotificationChannel)
    recipient = factory.Faker("user_name")
    title = factory.Faker("sentence", nb_words=5)
    body = factory.Faker("text", max_nb_chars=200)
    status = NotificationStatus.SENT
    read_at = None
