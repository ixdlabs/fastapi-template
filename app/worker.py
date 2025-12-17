import sys
from celery import Celery

from celery.signals import worker_process_init
from app.config.database import create_db_engine_from_settings
from app.config.logging import setup_logging
from app.config.otel import setup_open_telemetry
from app.config.settings import get_settings
from app.config.background import beat_schedule

from app.features.users import tasks as _  # noqa: F401

settings = get_settings()
setup_logging(settings.logger_name)

app = Celery("tasks", broker=settings.celery_broker_url)

app.conf.task_always_eager = settings.celery_task_always_eager
app.conf.timezone = settings.celery_timezone


@app.on_after_configure.connect
def setup_periodic_tasks(sender: Celery, **kwargs):
    for task_name, schedule in beat_schedule.items():
        sender.add_periodic_task(schedule, sender.tasks[task_name].s(), name=task_name)


@worker_process_init.connect(weak=False)
def init_celery_tracing(*args, **kwargs):
    db_engine = create_db_engine_from_settings(settings)
    setup_open_telemetry(app, db_engine, settings)


# Prevent starting a worker or beat process if Celery is in eager mode.
# ----------------------------------------------------------------------------------------------------------------------

if len(sys.argv) > 1 and sys.argv[-1] in {"worker", "beat"}:
    if settings.celery_task_always_eager:
        raise RuntimeError(
            "Celery is running in eager mode. Do not start a worker or beat process.\n"
            "💡 Set CELERY_TASK_ALWAYS_EAGER=false to run background workers."
        )
