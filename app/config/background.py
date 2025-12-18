"""
This module defines the Background class and its dependency for managing background tasks using Celery.
The Background class provides a method to submit tasks to be executed asynchronously.
"""

import asyncio
import functools
from typing import Annotated, Any, Callable, Coroutine, ParamSpec, TypeVar
from celery.schedules import crontab

from celery.app.task import Task as CeleryTask

from fastapi import Depends

from app.config.celery_app import get_celery_app


P = ParamSpec("P")
R = TypeVar("R")


# Dependency that provides application background task runner.
# The background is cached to avoid recreating it on each request.
# ----------------------------------------------------------------------------------------------------------------------


class Background:
    def submit(self, fn: Callable[P, R], *args: P.args, **kwargs: P.kwargs):
        """Submit a function to be run in the background as a Celery task."""
        if isinstance(fn, CeleryTask) or callable(getattr(fn, "apply_async", None)):
            fn.apply_async(args=args, kwargs=kwargs)
            return

        celery_app = get_celery_app()
        task = celery_app.task(fn)
        task.apply_async(args=args, kwargs=kwargs)


@functools.lru_cache
def get_background():
    return Background()


BackgroundDep = Annotated[Background, Depends(get_background)]

# Decorator to convert an async function into a Celery task.
# ----------------------------------------------------------------------------------------------------------------------


def background_task(func: Callable[P, Coroutine[R, Any, Any]]) -> Callable[P, R]:
    """Convert an async function into a Celery task."""

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        return asyncio.run(func(*args, **kwargs))

    celery_app = get_celery_app()
    return celery_app.task(wrapper)


# Decorator to create a periodic Celery task.
# All periodic tasks created with this decorator are automatically added to the beat_schedule variable.
# ----------------------------------------------------------------------------------------------------------------------


def periodic_task(schedule: crontab | float | int):
    """Decorator to create a periodic Celery task."""

    def decorator(func: Callable[P, Coroutine[R, Any, Any]]) -> Callable[P, R]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            return asyncio.run(func(*args, **kwargs))

        celery_app = get_celery_app()
        task = celery_app.task(wrapper)
        beat_schedule[task.name] = schedule
        return task

    return decorator


# Every function decorated with @periodic_task is automatically added to this dictionary.
beat_schedule: dict[str, crontab | float | int] = {}
