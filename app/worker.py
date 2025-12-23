import logging
import os
import time

from celery import Celery
from celery.signals import worker_process_init
from app.config.database import create_db_engine_from_settings
from app.config.logging import setup_logging
from app.config.otel import setup_open_telemetry
from app.config.settings import get_settings

from app.features import model_registry  # noqa: F401,E402
from app.features import task_registry

logger = logging.getLogger(__name__)

settings = get_settings()
setup_logging(settings)

os.environ["TZ"] = settings.server_timezone
time.tzset()

app = Celery("tasks", broker=settings.celery_broker_url)
app.conf.task_always_eager = settings.celery_task_always_eager
app.conf.timezone = settings.celery_timezone

# Ensure task modules are imported when the worker starts.
# This makes task registration deterministic without needing to rely on
# side-effect imports in worker entrypoints.
app.conf.imports = ("app.features.task_registry",)

# Register periodic tasks from the task registry.
# https://docs.celeryq.dev/en/main/userguide/periodic-tasks.html
app.conf.beat_schedule = {
    task.name: {
        "task": task.task,
        "schedule": task.schedule,
        "args": task.args,
    }
    for task in task_registry.periodic_tasks
}


@worker_process_init.connect(weak=False)
def init_celery_tracing(*args, **kwargs):
    db_engine = create_db_engine_from_settings(settings)
    setup_open_telemetry(app, db_engine, settings)


# Make this app the default/current app so task decorators bind to it.
app.set_current()
app.set_default()


if __name__ == "__main__":
    app.start()
