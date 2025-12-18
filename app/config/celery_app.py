"""
Central Celery application instance for both the API process (task producer)
and the Celery worker (task consumer).

Having a single shared app avoids "NotRegistered" errors caused by tasks being
registered on a different Celery app than the worker is running.
"""

from functools import lru_cache

from celery import Celery

from app.config.settings import get_settings


@lru_cache
def get_celery_app() -> Celery:
    settings = get_settings()

    app = Celery("tasks", broker=settings.celery_broker_url)
    app.conf.task_always_eager = settings.celery_task_always_eager
    app.conf.timezone = settings.celery_timezone

    # Ensure task modules are imported when the worker starts.
    # This makes task registration deterministic without needing to rely on
    # side-effect imports in worker entrypoints.
    app.conf.imports = ("app.features.task_registry",)

    # Make this app the default/current app so task decorators bind to it.
    app.set_current()
    app.set_default()
    return app
