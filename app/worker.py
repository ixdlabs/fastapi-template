import logging

from celery.signals import worker_process_init
from app.config.database import create_db_engine_from_settings
from app.config.logging import setup_logging
from app.config.otel import setup_open_telemetry
from app.config.celery_app import get_celery_app
from app.config.settings import get_settings
from app.config.background import beat_schedule

# Ensure models/tasks are imported for side effects (task registration, model registration).
from app.features import model_registry  # noqa: F401,E402
from app.features import task_registry  # noqa: F401,E402

logger = logging.getLogger(__name__)

settings = get_settings()
setup_logging(settings)

app = get_celery_app()


@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    if settings.celery_task_always_eager and beat_schedule:
        logger.warning("Celery is running in eager mode. Periodic tasks cannot be scheduled.")
    for task_name, schedule in beat_schedule.items():
        sender.add_periodic_task(schedule, sender.tasks[task_name].s(), name=task_name)


@worker_process_init.connect(weak=False)
def init_celery_tracing(*args, **kwargs):
    db_engine = create_db_engine_from_settings(settings)
    setup_open_telemetry(app, db_engine, settings)
