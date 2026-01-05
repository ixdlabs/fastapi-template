from unittest.mock import MagicMock
from pydantic import BaseModel
import pytest
from pytest import MonkeyPatch

from app.core.background import BackgroundTask, TaskRegistry, WorkerScope, get_worker_scope
from app.core.database import DbDep
from app.core.settings import Settings, SettingsDep, SettingsWorkerDep
from celery.app.task import Task as CeleryTask


class InputModel(BaseModel):
    value: int


class OutputModel(BaseModel):
    result: int


async def sample_task(task_input: InputModel, settings: SettingsWorkerDep) -> OutputModel:
    return OutputModel(result=task_input.value)


async def sample_periodic_task() -> OutputModel:
    return OutputModel(result=999)


# Background Tasks
# ----------------------------------------------------------------------------------------------------------------------


def test_background_task_returns_factory():
    task_registry = TaskRegistry()
    factory = task_registry.background_task("sample_task_1")(sample_task)
    assert callable(factory)


def test_periodic_task_adds_beat_schedule():
    task_registry = TaskRegistry()
    _ = task_registry.periodic_task("sample_task", schedule=60)(sample_task)

    assert "sample_task" in task_registry.beat_schedule
    assert task_registry.beat_schedule["sample_task"]["schedule"] == 60
    assert isinstance(task_registry.beat_schedule["sample_task"]["task"], str)
    assert task_registry.beat_schedule["sample_task"]["task"].endswith("sample_task")


def test_task_factory_creates_background_task(settings_fixture: Settings):
    task_registry = TaskRegistry()
    factory = task_registry.background_task("sample_task_2")(sample_task)
    background_task = factory(settings_fixture)

    assert isinstance(background_task, BackgroundTask)
    assert isinstance(background_task.celery_task, CeleryTask)


@pytest.mark.asyncio
async def test_wait_and_get_result_raises_error_if_not_submitted(settings_fixture: Settings):
    task_registry = TaskRegistry()
    factory = task_registry.background_task("sample_task_error")(sample_task)
    background_task = factory(settings_fixture)

    with pytest.raises(RuntimeError, match="Task has not been submitted yet"):
        await background_task.wait_and_get_result(OutputModel)  # pyright: ignore[reportUnusedCallResult]4


@pytest.mark.asyncio
async def test_background_task_submit_calls_celery_apply_async(monkeypatch: MonkeyPatch, settings_fixture: Settings):
    task_registry = TaskRegistry()
    factory = task_registry.background_task("sample_task_3")(sample_task)
    background_task = factory(settings_fixture)

    mock_apply_async = MagicMock()
    monkeypatch.setattr(background_task.celery_task, "apply_async", mock_apply_async)

    input_model = InputModel(value=42)
    await background_task.submit(input_model)

    mock_apply_async.assert_called_once()
    _, kwargs = mock_apply_async.call_args
    assert kwargs["kwargs"]["raw_task_input"] == input_model.model_dump_json()


# Task Registry
# ----------------------------------------------------------------------------------------------------------------------


def test_task_registry_initialization():
    registry = TaskRegistry()
    assert registry.beat_schedule == {}


def test_task_registry_periodic_task():
    registry = TaskRegistry()
    factory = registry.periodic_task("sample_task", schedule=120)(sample_task)

    assert callable(factory)
    assert "sample_task" in registry.beat_schedule
    assert registry.beat_schedule["sample_task"]["schedule"] == 120
    assert isinstance(registry.beat_schedule["sample_task"]["task"], str)
    assert registry.beat_schedule["sample_task"]["task"].endswith("sample_task")


def test_task_registry_background_task_without_schedule():
    registry = TaskRegistry()
    factory = registry.background_task("sample_task")(sample_task)

    assert callable(factory)
    assert "sample_task" not in registry.beat_schedule


def test_periodic_task_runs_and_returns_json():
    registry = TaskRegistry()
    celery_task = registry.periodic_task("test_periodic_task", schedule=60)(sample_periodic_task)
    result = celery_task.apply()

    assert result.result == '{"result":999}'


# Background Task Execution
# ----------------------------------------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_task_factory_submission_executes_task(settings_fixture: Settings):
    task_registry = TaskRegistry()
    factory = task_registry.background_task("sample_task_4")(sample_task)
    background_task = factory(settings_fixture)

    input_model = InputModel(value=10)
    await background_task.submit(input_model)
    result = await background_task.wait_and_get_result(OutputModel)
    assert result.result == 10


@pytest.mark.asyncio
async def test_task_with_dependencies_execution(settings_fixture: Settings, db_fixture: DbDep):
    task_registry = TaskRegistry()
    called_settings: list[Settings] = []

    async def sample_endpoint(task_input: InputModel, settings: SettingsDep) -> OutputModel:
        called_settings.append(settings)
        return OutputModel(result=task_input.value * 2)

    async def sample_endpoint_task(task_input: InputModel, settings: SettingsWorkerDep) -> OutputModel:
        return await sample_endpoint(task_input, settings=settings)

    factory = task_registry.background_task("sample_endpoint_5")(sample_endpoint_task)
    background_task = factory(settings_fixture)

    input_model = InputModel(value=5)
    await background_task.submit(input_model)
    task_output = await background_task.wait_and_get_result(OutputModel)
    assert task_output.result == 10
    assert len(called_settings) == 1
    assert called_settings[0] is settings_fixture


# Test WorkerScope
# ----------------------------------------------------------------------------------------------------------------------


def test_worker_scope_auth_user_returns_dummy_user():
    mock_task = MagicMock()
    mock_task.request.id = "test-uuid-1111"
    scope = WorkerScope(task=mock_task)
    user = scope.auth_user

    assert user.worker_id == "test-uuid-1111"
    assert user.type == "task_runner"


def test_get_worker_scope_raises_error_in_main_context():
    with pytest.raises(NotImplementedError, match="This dependency should only be used in worker context"):
        get_worker_scope()
