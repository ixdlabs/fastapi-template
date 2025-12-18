import factory

from app.features.users.tests.fixtures import UserFactory
from app.features.notifications.models import (
    Notification,
    NotificationChannel,
    NotificationDelivery,
    NotificationStatus,
    NotificationType,
)


class NotificationFactory(factory.Factory):
    class Meta:
        model = Notification

    user = factory.SubFactory(UserFactory)
    type = factory.Iterator(NotificationType)
    data = factory.LazyFunction(dict)


class NotificationDeliveryFactory(factory.Factory):
    class Meta:
        model = NotificationDelivery

    notification = factory.SubFactory(NotificationFactory)
    channel = factory.Iterator(NotificationChannel)
    recipient = factory.Faker("user_name")
    title = factory.Faker("sentence", nb_words=5)
    body = factory.Faker("text", max_nb_chars=200)
    status = NotificationStatus.SENT
