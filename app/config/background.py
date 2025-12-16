"""
This module defines the Background class and its dependency for managing background tasks using Celery.
The Background class provides a method to submit tasks to be executed asynchronously.
"""

import asyncio
from functools import lru_cache
import functools
from typing import Annotated, Any, Callable, Coroutine, ParamSpec, TypeVar

from celery import shared_task

from fastapi import Depends

P = ParamSpec("P")
R = TypeVar("R")


class Background:
    def submit(self, fn: Callable[P, R], *args: P.args, **kwargs: P.kwargs):
        from app.worker import app as celery_app

        task = celery_app.task(fn)
        task.apply_async(args=args, kwargs=kwargs)


# Dependency that provides application background task runner.
# The background is cached to avoid recreating it on each request.
# ----------------------------------------------------------------------------------------------------------------------


@lru_cache
def get_background():
    return Background()


BackgroundDep = Annotated[Background, Depends(get_background)]

# Decorator to convert an async function into a Celery task
# ----------------------------------------------------------------------------------------------------------------------


def background_task(func: Callable[P, Coroutine[R, Any, Any]]) -> Callable[P, R]:
    """Convert an async function into a Celery task."""

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        return asyncio.run(func(*args, **kwargs))

    return shared_task(wrapper)
