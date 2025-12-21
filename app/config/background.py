"""
This module defines the Background class and its dependency for managing background tasks using Celery.
The Background class provides a method to submit tasks to be executed asynchronously.
"""

import asyncio
import functools
import threading
from typing import Annotated, Any, Awaitable, Callable, Coroutine, ParamSpec, TypeVar


from celery import shared_task

from celery.app.task import Task as CeleryTask

from fastapi import Depends

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


# Utility to create shared async Celery tasks.
# Normally, Celery tasks are synchronous functions. This utility allows defining async functions as Celery tasks.
# Internally, it runs the async function in an event loop, either in the current thread or in a separate thread.
# ----------------------------------------------------------------------------------------------------------------------


def shared_async_task(name: str):
    """Convert an async function into a Celery task."""

    def decorator(func: Callable[P, Coroutine[R, Any, Any]]) -> Callable[P, R]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            try:
                asyncio.get_running_loop()
            except RuntimeError:
                return asyncio.run(func(*args, **kwargs))

            result_container: dict[str, R] = {}
            error_container: dict[str, BaseException] = {}

            def runner():
                try:
                    result_container["result"] = asyncio.run(func(*args, **kwargs))
                except BaseException as exc:
                    error_container["error"] = exc

            thread = threading.Thread(target=runner, daemon=True)
            thread.start()
            thread.join()

            if "error" in error_container:
                raise error_container["error"]
            return result_container["result"]

        return shared_task(name=name)(wrapper)

    return decorator
