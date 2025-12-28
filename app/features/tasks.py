from app.core.background import TaskRegistry
from app.features.users.tasks import user_task_registry

task_registry = TaskRegistry()
task_registry.include_registry(user_task_registry)
