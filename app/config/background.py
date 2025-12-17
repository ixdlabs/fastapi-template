"""
This module defines the Background class and its dependency for managing background tasks using Celery.
The Background class provides a method to submit tasks to be executed asynchronously.
"""

import abc
import asyncio
from functools import lru_cache
import functools
from typing import Annotated, Any, Callable, Coroutine, ParamSpec, TypeVar
from celery.schedules import crontab

from celery import shared_task

from fastapi import Depends

P = ParamSpec("P")
R = TypeVar("R")


class Background(abc.ABC):
    @abc.abstractmethod
    def submit(self, fn: Callable[P, R], *args: P.args, **kwargs: P.kwargs) -> None:
        """Submit a background task to be executed asynchronously."""


class CeleryBackground(Background):
    def submit(self, fn: Callable[P, R], *args: P.args, **kwargs: P.kwargs):
        task = shared_task(fn)
        task.apply_async(args=args, kwargs=kwargs)


class NoOpBackground(Background):
    def submit(self, fn: Callable[P, R], *args: P.args, **kwargs: P.kwargs):
        pass


# Dependency that provides application background task runner.
# The background is cached to avoid recreating it on each request.
# ----------------------------------------------------------------------------------------------------------------------


@lru_cache
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


beat_schedule: dict[str, crontab | float | int] = {}
