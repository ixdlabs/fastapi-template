"""
This module defines the Background class and its dependency for managing background tasks using Celery.
The Background class provides a method to submit tasks to be executed asynchronously.
"""

from collections.abc import Callable, Coroutine
import functools
import logging
from typing import AsyncGenerator, ParamSpec, Protocol, TypeVar
import uuid
from fastapi.dependencies.utils import get_typed_signature

from celery import shared_task
from celery.app.task import Context
from celery.app.task import Task as CeleryTask

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthUser, CurrentTaskRunnerDep
from app.core.database import DbDep, get_worker_db_session
from app.core.helpers import run_as_sync
from app.core.settings import Settings, SettingsDep, get_settings

logger = logging.getLogger(__name__)
P = ParamSpec("P")
R = TypeVar("R")

# Dependency that provides application background task runner.
# The background is cached to avoid recreating it on each request.
# ----------------------------------------------------------------------------------------------------------------------


class BackgroundTask:
    def __init__(self, celery_task: "CeleryTask[[str], str]", settings: Settings):
        super().__init__()
        self.settings = settings
        self.celery_task = celery_task

    async def submit(self, input_model: BaseModel):
        """Submit a function to be run in the background as a Celery task."""
        result = self.celery_task.apply_async(args=(input_model.model_dump_json(),))
        logger.info(f"Submitted background task {self.celery_task.name} with id {result.id}")


# Type definition for background task functions
# ----------------------------------------------------------------------------------------------------------------------


class TaskRegistryBackgroundTask[InT: BaseModel, OutT: BaseModel](Protocol):
    __module__: str
    __name__: str

    def __call__(
        self, task_input: InT, *, db: DbDep, settings: SettingsDep, current_user: CurrentTaskRunnerDep
    ) -> Coroutine[object, object, OutT]: ...


# Task Registry
# This acts similar to FastAPI's APIRouter but for background tasks.
# ----------------------------------------------------------------------------------------------------------------------


class TaskRegistry:
    def __init__(self):
        super().__init__()
        self.beat_schedule: dict[str, dict[str, object]] = {}
        self.worker_get_settings: Callable[[], SettingsDep] = get_settings
        self.worker_get_db_session: Callable[[SettingsDep], AsyncGenerator[AsyncSession, None]] = get_worker_db_session

    def register_background_task[InT: BaseModel, OutT: BaseModel](
        self, func: TaskRegistryBackgroundTask[InT, OutT], *, schedule: int | None = None
    ) -> Callable[[SettingsDep], BackgroundTask]:
        """Register a background task."""
        task_name = func.__name__
        task_full_name = f"{func.__module__}.{func.__name__}"

        # Inspect the type of first parameter to determine input model type
        wrapped_signature = get_typed_signature(func)
        task_input_param = next(iter(wrapped_signature.parameters.values()), None)
        assert task_input_param is not None and issubclass(task_input_param.annotation, BaseModel)

        # Async function that wraps the original function to handle dependency injection
        async def async_func(ctx: Context, raw_task_input: str, **kwargs: object) -> str:
            settings = self.worker_get_settings()
            settings = get_settings()
            async for db in self.worker_get_db_session(settings):
                current_user = AuthUser(id=uuid.uuid4(), type="task_runner", worker_id=ctx.id)
                input_model: type[InT] = task_input_param.annotation
                task_input = input_model.model_validate_json(raw_task_input)
                result = await func(task_input, db=db, settings=settings, current_user=current_user)
                return result.model_dump_json()
            raise RuntimeError("Failed to get database session for background task")

        # Wrapper function to convert async function to sync for Celery
        @functools.wraps(func)
        def wrapper(self: "CeleryTask[[str], str]", raw_task_input: str, **kwargs: object) -> str:
            return run_as_sync(async_func, self.request, raw_task_input, **kwargs)

        # If the schedule is provided, add it to the beat schedule
        # This will be picked up by Celery Beat to schedule periodic tasks
        if schedule is not None:
            self.beat_schedule[task_name] = {"task": task_full_name, "schedule": schedule}

        # This requires settings as a dependency, which will be provided by FastAPI
        # We do not use overrides here because overrides are meant for celery workers
        # But this will be called in the FastAPI context, we can directly get settings via dependency injection
        def task_factory(app_settings: SettingsDep) -> BackgroundTask:
            task = shared_task(name=task_name, bind=True)(wrapper)
            return BackgroundTask(celery_task=task, settings=app_settings)

        return task_factory

    def include_registry(self, registry: "TaskRegistry"):
        """Include another TaskRegistry's tasks."""
        self.beat_schedule.update(registry.beat_schedule)
