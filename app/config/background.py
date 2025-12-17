"""
This module defines the Background class and its dependency for managing background tasks using Celery.
The Background class provides a method to submit tasks to be executed asynchronously.
"""

import asyncio
import functools
from typing import Annotated, Any, Callable, Coroutine, ParamSpec, TypeVar
from celery.schedules import crontab

from celery import shared_task

from fastapi import BackgroundTasks, Depends

from app.config.settings import Settings, SettingsDep

P = ParamSpec("P")
R = TypeVar("R")


class Background:
    def __init__(self, settings: Settings, background_tasks: BackgroundTasks):
        self.settings = settings
        self.background_tasks = background_tasks

    def submit(self, fn: Callable[P, R], *args: P.args, **kwargs: P.kwargs):
        # If Celery is configured to run tasks eagerly, run the function directly in the background task.
        if self.settings.celery_task_always_eager:
            self.background_tasks.add_task(fn, *args, **kwargs)
            return

        task = shared_task(fn)
        task.apply_async(args=args, kwargs=kwargs)

    @staticmethod
    def create(settings: Settings, background_tasks: BackgroundTasks):
        return Background(settings, background_tasks)


# Dependency that provides application background task runner.
# The background is cached to avoid recreating it on each request.
# ----------------------------------------------------------------------------------------------------------------------


def get_background(settings: SettingsDep, background_tasks: BackgroundTasks):
    return Background(settings, background_tasks)


BackgroundDep = Annotated[Background, Depends(get_background)]

# Decorator to convert an async function into a Celery task.
# ----------------------------------------------------------------------------------------------------------------------


def background_task(func: Callable[P, Coroutine[R, Any, Any]]) -> Callable[P, R]:
    """Convert an async function into a Celery task."""

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        return asyncio.run(func(*args, **kwargs))

    return shared_task(wrapper)


# Decorator to create a periodic Celery task.
# All periodic tasks created with this decorator are automatically added to the beat_schedule variable.
# ----------------------------------------------------------------------------------------------------------------------


def periodic_task(schedule: crontab | float | int):
    """Decorator to create a periodic Celery task."""

    def decorator(func: Callable[P, Coroutine[R, Any, Any]]) -> Callable[P, R]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            return asyncio.run(func(*args, **kwargs))

        task = shared_task(wrapper)
        beat_schedule[task.name] = schedule
        return task

    return decorator


# Every function decorated with @periodic_task is automatically added to this dictionary.
beat_schedule: dict[str, crontab | float | int] = {}
