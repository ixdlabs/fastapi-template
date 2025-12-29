"""
This module defines the Background class and its dependency for managing background tasks using Celery.
The Background class provides a method to submit tasks to be executed asynchronously.
"""

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
import functools
import logging
from typing import ParamSpec, TypeVar
import uuid
from fastapi.dependencies.utils import get_typed_signature

from celery import shared_task
from celery.app.task import Context
from celery.app.task import Task as CeleryTask

from pydantic import BaseModel

from app.core.auth import AuthUser
from app.core.helpers import run_as_sync
from app.core.settings import SettingsDep

logger = logging.getLogger(__name__)
P = ParamSpec("P")
R = TypeVar("R")

# Dependency that provides application background task runner.
# The background is cached to avoid recreating it on each request.
# ----------------------------------------------------------------------------------------------------------------------


class BackgroundTask:
    def __init__(self, celery_task: "CeleryTask[[str], str]", settings: SettingsDep):
        super().__init__()
        self.celery_task = celery_task
        self.settings = settings

    async def submit(self, input_model: BaseModel) -> None:
        """Submit a function to be run in the background as a Celery task."""
        task_input_raw = input_model.model_dump_json()
        result = self.celery_task.apply_async(args=(task_input_raw,))
        logger.info(f"Submitted background task {self.celery_task.name} with id {result.id}")


# Worker scope containing all current worker information.
# ----------------------------------------------------------------------------------------------------------------------


@dataclass
class WorkerScope:
    context: Context

    def to_auth_user(self) -> AuthUser:
        return AuthUser(id=uuid.uuid4(), type="task_runner", worker_id=self.context.id)


# Task Registry
# This acts similar to FastAPI's APIRouter but for background tasks.
# ----------------------------------------------------------------------------------------------------------------------

type BackgroundTaskCallable[P: BaseModel, R: BaseModel] = Callable[[P, WorkerScope], Coroutine[None, None, R]]
type BackgroundTaskFactory = Callable[[SettingsDep], BackgroundTask]


class TaskRegistry:
    def __init__(self):
        super().__init__()
        self.beat_schedule: dict[str, dict[str, object]] = {}

    def background_task[P: BaseModel, R: BaseModel](
        self, task_name: str, *, schedule: int | None = None
    ) -> Callable[[BackgroundTaskCallable[P, R]], BackgroundTaskFactory]:
        """Register a background task."""

        def decorator(func: BackgroundTaskCallable[P, R]) -> BackgroundTaskFactory:
            task_full_name = f"{func.__module__}.{func.__name__}"

            # Inspect the type of first parameter to determine input model type
            wrapped_signature = get_typed_signature(func)
            task_input_param = next(iter(wrapped_signature.parameters.values()), None)
            assert task_input_param is not None and issubclass(task_input_param.annotation, BaseModel)

            # Async function that wraps the original function to handle dependency injection
            async def async_func(ctx: Context, raw_task_input: str, **kwargs: object) -> str:
                input_model: type[P] = task_input_param.annotation
                task_input = input_model.model_validate_json(raw_task_input)
                result = await func(task_input, WorkerScope(context=ctx))
                return result.model_dump_json()

            # Wrapper function to convert async function to sync for Celery
            @functools.wraps(func)
            def wrapper(self: "CeleryTask[[str], str]", raw_task_input: str, **kwargs: object) -> str:
                return run_as_sync(async_func, self.request, raw_task_input, **kwargs)

            # If the schedule is provided, add it to the beat schedule
            # This will be picked up by Celery Beat to schedule periodic tasks
            if schedule is not None:
                self.beat_schedule[task_name] = {"task": task_full_name, "schedule": schedule}

            def factory(settings: SettingsDep) -> BackgroundTask:
                task = shared_task(name=task_name, bind=True)(wrapper)
                return BackgroundTask(celery_task=task, settings=settings)

            return factory

        return decorator

    def include_registry(self, registry: "TaskRegistry"):
        """Include another TaskRegistry's tasks."""
        self.beat_schedule.update(registry.beat_schedule)
