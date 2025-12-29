import logging

from celery import Celery
from celery.signals import worker_process_init
from app.core.database import create_db_engine_from_settings
from app.core.logging import setup_logging
from app.core.otel import setup_open_telemetry
from app.core.settings import Settings, get_settings

from app.features import models  # noqa: F401
from app.features import tasks

logger = logging.getLogger(__name__)


def create_celery_app(settings: Settings) -> Celery:
    setup_logging(settings)

    app = Celery("tasks", broker=settings.celery_broker_url)
    app.conf.task_always_eager = settings.celery_task_always_eager
    app.conf.timezone = settings.celery_timezone

    # Ensure task modules are imported when the worker starts.
    # This makes task registration deterministic without needing to rely on
    # side-effect imports in worker entrypoints.
    app.conf.imports = ("app.features.tasks",)

    # Register periodic tasks from the task registry.
    # https://docs.celeryq.dev/en/main/userguide/periodic-tasks.html
    app.conf.beat_schedule = tasks.registry.beat_schedule

    # Initialize OpenTelemetry tracing for Celery workers.
    # This has to be done in the worker_process_init signal handler to ensure
    # that each worker process sets up its own tracing.
    def init_celery_tracing(*args: object, **kwargs: object) -> None:
        db_engine = create_db_engine_from_settings(settings)
        setup_open_telemetry(app, db_engine, settings)

    _ = worker_process_init.connect(weak=False)(init_celery_tracing)

    # Make this app the default/current app so task decorators bind to it.
    app.set_current()
    app.set_default()

    return app


global_settings = get_settings()
app = create_celery_app(global_settings)

if __name__ == "__main__":
    app.start()
