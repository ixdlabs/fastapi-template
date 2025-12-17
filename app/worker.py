import logging
from celery import Celery

from celery.signals import worker_process_init
from app.config.database import create_db_engine_from_settings
from app.config.logging import setup_logging
from app.config.otel import setup_open_telemetry
from app.config.settings import get_settings
from app.config.background import beat_schedule

from app.features import model_registry  # noqa: F401
from app.features import task_registry  # noqa: F401

logger = logging.getLogger(__name__)

settings = get_settings()
setup_logging(settings)

app = Celery("tasks", broker=settings.celery_broker_url)

app.conf.task_always_eager = settings.celery_task_always_eager
app.conf.timezone = settings.celery_timezone


@app.on_after_configure.connect
def setup_periodic_tasks(sender: Celery, **kwargs):
    if settings.celery_task_always_eager and beat_schedule:
        logger.warning("Celery is running in eager mode. Periodic tasks cannot be scheduled.")
    for task_name, schedule in beat_schedule.items():
        sender.add_periodic_task(schedule, sender.tasks[task_name].s(), name=task_name)


@worker_process_init.connect(weak=False)
def init_celery_tracing(*args, **kwargs):
    db_engine = create_db_engine_from_settings(settings)
    setup_open_telemetry(app, db_engine, settings)
