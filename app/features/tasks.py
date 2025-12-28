from app.core.background import TaskRegistry
from app.features.users.tasks import user_registry

registry = TaskRegistry()
registry.include_registry(user_registry)
