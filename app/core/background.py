"""
This module defines the Background class and its dependency for managing background tasks using Celery.
The Background class provides a method to submit tasks to be executed asynchronously.
"""

from collections.abc import Callable
import functools
import logging
from typing import ParamSpec, Protocol, TypeVar
import uuid
from fast_depends import dependency_provider, inject
from fastapi.dependencies.utils import get_typed_signature

from celery import shared_task
from celery.app.task import Context as CeleryContext
from celery.app.task import Task as CeleryTask

from pydantic import BaseModel

from app.core.auth import AuthUser, get_current_user
from app.core.helpers import run_as_sync
from app.core.settings import SettingsDep

logger = logging.getLogger(__name__)

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


# Task Registry
# This acts similar to FastAPI's APIRouter but for background tasks.
# ----------------------------------------------------------------------------------------------------------------------

type BackgroundTaskFactory = Callable[[SettingsDep], BackgroundTask]
type WorkerContext = CeleryContext

P = TypeVar("P", bound=BaseModel, contravariant=True)
R = TypeVar("R", bound=BaseModel, covariant=True)
X = ParamSpec("X")


class BackgroundTaskCallable(Protocol[P, R, X]):
    __name__: str

    async def __call__(self, task_input: P, *args: X.args, **kwargs: X.kwargs) -> R: ...


class TaskRegistry:
    def __init__(self):
        super().__init__()
        self.beat_schedule: dict[str, dict[str, object]] = {}

    def background_task(self, task_name: str, *, schedule: int | None = None):
        """Register a background task."""

        def decorator(
            func: BackgroundTaskCallable[P, R, X],
        ) -> BackgroundTaskFactory:
            task_full_name = f"{func.__module__}.{func.__name__}"
            # If the schedule is provided, add it to the beat schedule
            # This will be picked up by Celery Beat to schedule periodic tasks
            if schedule is not None:
                self.beat_schedule[task_name] = {"task": task_full_name, "schedule": schedule}

            wrapped_signature = get_typed_signature(func)
            task_input_param = next(iter(wrapped_signature.parameters.values()), None)
            assert task_input_param is not None and issubclass(task_input_param.annotation, BaseModel)

            # Async function that wraps the original function to handle dependency injection
            # Celery will call this via the wrapper function below
            async def async_func(ctx: CeleryContext, raw_task_input: str, **kwargs: object) -> str:
                input_model: type[P] = task_input_param.annotation
                task_input = input_model.model_validate_json(raw_task_input)
                current_user = AuthUser(id=uuid.uuid4(), type="task_runner", worker_id=str(ctx.id))
                with dependency_provider.scope(get_current_user, lambda: current_user):
                    injected_func = inject(func)
                    result: R = await injected_func(task_input)  # pyright: ignore[reportCallIssue]
                    return result.model_dump_json()

            # Wrapper function to convert async function to sync for Celery
            # This is the function that Celery will actually call
            @functools.wraps(func)
            def wrapper(self: "CeleryTask[[str], str]", raw_task_input: str, **kwargs: object) -> str:
                return run_as_sync(async_func, self.request, raw_task_input, **kwargs)

            # This should be in this scope to make sure this is defined at the time of decorator call
            # Otherwise celery might not pick up the task correctly
            task = shared_task(name=task_name, bind=True)(wrapper)

            # This will be called by FastAPI to provide the dependency
            # The settings object here is the one in FastAPI context
            def dependency(settings: SettingsDep) -> BackgroundTask:
                return BackgroundTask(celery_task=task, settings=settings)

            return dependency

        return decorator

    def include_registry(self, registry: "TaskRegistry"):
        """Include another TaskRegistry's tasks."""
        self.beat_schedule.update(registry.beat_schedule)
