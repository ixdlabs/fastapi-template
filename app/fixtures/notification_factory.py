import factory

from app.features.notifications.models.notification import Notification, NotificationType
from app.fixtures.user_factory import UserFactory


class NotificationFactory(factory.Factory[Notification]):
    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        model = Notification

    user = factory.SubFactory(UserFactory)
    type = factory.Iterator(NotificationType)
    data = factory.LazyFunction(dict)
