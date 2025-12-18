"""
This module defines the Background class and its dependency for managing background tasks using Celery.
The Background class provides a method to submit tasks to be executed asynchronously.
"""

import asyncio
import functools
import threading
from typing import Annotated, Any, Awaitable, Callable, Coroutine, ParamSpec, TypeVar
from celery.schedules import crontab

from celery.app.task import Task as CeleryTask

from fastapi import Depends

from app.config.celery_app import get_celery_app
from app.config.settings import Settings, SettingsDep


P = ParamSpec("P")
R = TypeVar("R")


# Dependency that provides application background task runner.
# The background is cached to avoid recreating it on each request.
# ----------------------------------------------------------------------------------------------------------------------


class Background:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def submit(self, fn: Callable[P, Awaitable[R]], *args: P.args, **kwargs: P.kwargs):
        """Submit a function to be run in the background as a Celery task."""
        if not isinstance(fn, CeleryTask):
            raise ValueError("Function must be a Celery task wrapped with @background_task")
        fn.apply_async(args=args, kwargs=kwargs)


def get_background(settings: SettingsDep):
    return Background(settings)


BackgroundDep = Annotated[Background, Depends(get_background)]

# Decorator to convert an async function into a Celery task.
# ----------------------------------------------------------------------------------------------------------------------


def background_task(func: Callable[P, Coroutine[R, Any, Any]]) -> Callable[P, R]:
    """Convert an async function into a Celery task."""

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        return _run_async_sync(func, *args, **kwargs)

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
            return _run_async_sync(func, *args, **kwargs)

        celery_app = get_celery_app()
        task = celery_app.task(wrapper)
        beat_schedule[task.name] = schedule
        return task

    return decorator


# Every function decorated with @periodic_task is automatically added to this dictionary.
beat_schedule: dict[str, crontab | float | int] = {}

# Run a coroutine from synchronous code.
# ----------------------------------------------------------------------------------------------------------------------


def _run_async_sync(async_func: Callable[P, Coroutine[Any, Any, R]], *args: P.args, **kwargs: P.kwargs) -> R:
    """
    Run a coroutine from synchronous code.

    Celery tasks are synchronous callables, but some of our task implementations are async.
    In eager mode (often used in development/tests), Celery may execute the task inline while
    FastAPI's event loop is already running, so `asyncio.run()` would crash.
    """

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(async_func(*args, **kwargs))

    result_container: dict[str, R] = {}
    error_container: dict[str, BaseException] = {}

    def runner():
        try:
            result_container["result"] = asyncio.run(async_func(*args, **kwargs))
        except BaseException as exc:
            error_container["error"] = exc

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()
    thread.join()

    if "error" in error_container:
        raise error_container["error"]
    return result_container["result"]
