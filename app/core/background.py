"""
This module defines the Background class and its dependency for managing background tasks using Celery.
The Background class provides a method to submit tasks to be executed asynchronously.
"""

import abc
from collections.abc import Callable
import functools
import logging
from typing import Annotated, ParamSpec, Protocol, TypeVar, override
import uuid
from fast_depends import dependency_provider, inject, Depends as WorkerDepends
from fastapi.dependencies.utils import get_typed_signature

from celery.result import AsyncResult
from celery import shared_task
from celery.app.task import Task as CeleryTask

from pydantic import BaseModel

from app.core.auth import AuthUser
from app.core.helpers import run_as_sync
from app.core.settings import SettingsDep

logger = logging.getLogger(__name__)

type BackgroundTaskFactory = Callable[[SettingsDep], BackgroundTask]

# Background Task Interface
# ----------------------------------------------------------------------------------------------------------------------


class BackgroundTask(abc.ABC):
    @abc.abstractmethod
    async def submit(self, input_model: BaseModel) -> None:
        """Submit a function to be run in the background."""

    @abc.abstractmethod
    async def wait_and_get_result[T: BaseModel](self, output_cls: type[T], timeout: float | None = None) -> T:
        """Wait for the task to complete and get the result as a Pydantic model."""


# Background Task Implementation using Celery
# ----------------------------------------------------------------------------------------------------------------------
class CeleryBackgroundTask(BackgroundTask):
    def __init__(self, celery_task: "CeleryTask[[str], str]", settings: SettingsDep):
        super().__init__()
        self.celery_task = celery_task
        self.settings = settings
        self.result: AsyncResult[str] | None = None

    @override
    async def submit(self, input_model: BaseModel) -> None:
        task_input_raw = input_model.model_dump_json()
        self.result = self.celery_task.apply_async(kwargs={"raw_task_input": task_input_raw})
        logger.info(f"Submitted background task {self.celery_task.name} with id {self.result.id}")

    @override
    async def wait_and_get_result[T: BaseModel](self, output_cls: type[T], timeout: float | None = None) -> T:
        if self.result is None:
            raise RuntimeError("Task has not been submitted yet.")
        raw_result = self.result.get(timeout=timeout)
        return output_cls.model_validate_json(raw_result)


# Task Registry
# This acts similar to FastAPI's APIRouter but for background tasks.
# ----------------------------------------------------------------------------------------------------------------------


P = TypeVar("P", bound=BaseModel, contravariant=True)
R = TypeVar("R", bound=BaseModel, covariant=True)
X = ParamSpec("X")


class BackgroundTaskCallable(Protocol[P, R, X]):
    __name__: str

    async def __call__(self, task_input: P, *args: X.args, **kwargs: X.kwargs) -> R: ...


class PeriodicTaskCallable(Protocol[R, X]):
    __name__: str

    async def __call__(self, *args: X.args, **kwargs: X.kwargs) -> R: ...


class TaskRegistry:
    def __init__(self):
        super().__init__()
        self.beat_schedule: dict[str, dict[str, object]] = {}

    def background_task(self, task_name: str):
        """Register a background task."""

        def decorator(
            func: BackgroundTaskCallable[P, R, X],
        ) -> BackgroundTaskFactory:
            wrapped_signature = get_typed_signature(func)
            task_input_param = next(iter(wrapped_signature.parameters.values()), None)
            assert task_input_param is not None and issubclass(task_input_param.annotation, BaseModel)

            # Async function that wraps the original function to handle dependency injection
            # Celery will call this via the wrapper function below
            async def async_func(self: "CeleryTask[[str], str]", raw_task_input: str) -> str:
                input_model: type[P] = task_input_param.annotation
                task_input = input_model.model_validate_json(raw_task_input)
                worker_scope = WorkerScope(task=self)
                with dependency_provider.scope(get_worker_scope, lambda: worker_scope):
                    injected_func = inject(func)
                    result: R = await injected_func(task_input)  # pyright: ignore[reportCallIssue]
                    return result.model_dump_json()

            # Wrapper function to convert async function to sync for Celery
            # This is the function that Celery will actually call
            @functools.wraps(func)
            def wrapper(self: "CeleryTask[[str], str]", raw_task_input: str) -> str:
                return run_as_sync(async_func, self, raw_task_input)

            # This should be in this scope to make sure this is defined at the time of decorator call
            # Otherwise celery might not pick up the task correctly
            task = shared_task(name=task_name, bind=True)(wrapper)

            # This will be called by FastAPI to provide the dependency
            # The settings object here is the one in FastAPI context
            def dependency(settings: SettingsDep) -> BackgroundTask:
                return CeleryBackgroundTask(celery_task=task, settings=settings)

            return dependency

        return decorator

    def periodic_task(self, task_name: str, schedule: int):
        """Decorator to register a periodic background task."""

        def decorator(func: PeriodicTaskCallable[R, X]) -> CeleryTask[[], str]:
            task_full_name = f"{func.__module__}.{func.__name__}"
            # Add to beat schedule
            self.beat_schedule[task_name] = {"task": task_full_name, "schedule": schedule}

            # Async function that wraps the original function to handle dependency injection
            async def async_func(self: "CeleryTask[[], str]") -> str:
                worker_scope = WorkerScope(task=self)
                with dependency_provider.scope(get_worker_scope, lambda: worker_scope):
                    injected_func = inject(func)
                    result: R = await injected_func()  # pyright: ignore[reportCallIssue]
                    return result.model_dump_json()

            # Wrapper function to convert async function to sync for Celery
            # This is the function that Celery will actually call
            @functools.wraps(func)
            def wrapper(self: "CeleryTask[[], str]") -> str:
                return run_as_sync(async_func, self)

            # This should be in this scope to make sure this is defined at the time of decorator call
            # Otherwise celery might not pick up the task correctly
            return shared_task(name=task_name, bind=True)(wrapper)

        return decorator

    def include_registry(self, registry: "TaskRegistry"):
        """Include another TaskRegistry's tasks."""
        self.beat_schedule.update(registry.beat_schedule)


# Dependency to get the worker context in Celery tasks
# ----------------------------------------------------------------------------------------------------------------------


class WorkerScope:
    def __init__(self, task: "CeleryTask[..., str]"):
        super().__init__()
        self.task: "CeleryTask[..., str]" = task

    @property
    def auth_user(self) -> AuthUser:
        """Returns a dummy AuthUser representing the task runner."""
        return AuthUser(id=uuid.uuid4(), type="task_runner", worker_id=str(self.task.request.id))


# This dependency will be overridden in the worker context to provide the WorkerScope
# In FastAPI context, it will raise an error if used
def get_worker_scope() -> None:
    raise NotImplementedError("This dependency should only be used in worker context")


WorkerScopeDep = Annotated[WorkerScope, WorkerDepends(get_worker_scope)]
