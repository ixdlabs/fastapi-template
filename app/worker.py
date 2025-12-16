from celery import Celery

from celery.signals import worker_process_init
from app.config.database import create_db_engine_from_settings
from app.config.logging import setup_logging
from app.config.otel import setup_open_telemetry
from app.config.settings import get_settings
from app.features.users import tasks as _  # noqa: F401

settings = get_settings()
setup_logging(settings.logger_name)

app = Celery("tasks", broker=settings.celery_broker_url)

app.conf.task_always_eager = settings.celery_task_always_eager


@worker_process_init.connect(weak=False)
def init_celery_tracing(*args, **kwargs):
    db_engine = create_db_engine_from_settings(settings)
    setup_open_telemetry(app, db_engine, settings)
