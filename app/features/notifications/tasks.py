import logging

from app.core.background import TaskRegistry

from app.features.notifications.services.tasks import send_notification


logger = logging.getLogger(__name__)
notification_registry = TaskRegistry()
notification_registry.include_registry(send_notification.registry)
