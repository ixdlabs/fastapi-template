from app.core.background import TaskRegistry
from app.features.users.tasks import user_registry
from app.features.notifications.tasks import notification_registry

registry = TaskRegistry()
registry.include_registry(user_registry)
registry.include_registry(notification_registry)
