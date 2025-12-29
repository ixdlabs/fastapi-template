from unittest.mock import MagicMock
from pydantic import BaseModel
import pytest
from pytest import MonkeyPatch
from app.core.auth import CurrentTaskRunnerDep
from app.core.background import BackgroundTask, TaskRegistry, WorkerScope
from app.core.database import DbDep
from app.core.settings import Settings, SettingsDep
from celery.app.task import Task as CeleryTask


class InputModel(BaseModel):
    value: int


class OutputModel(BaseModel):
    result: int


async def sample_task(task_input: InputModel, scope: WorkerScope) -> OutputModel:
    return OutputModel(result=task_input.value)


# Background Tasks
# ----------------------------------------------------------------------------------------------------------------------


def test_background_task_returns_factory():
    task_registry = TaskRegistry()
    factory = task_registry.background_task("sample_task")(sample_task)
    assert callable(factory)


def test_background_task_adds_beat_schedule():
    task_registry = TaskRegistry()
    _ = task_registry.background_task("sample_task", schedule=60)(sample_task)

    assert "sample_task" in task_registry.beat_schedule
    assert task_registry.beat_schedule["sample_task"]["schedule"] == 60
    assert isinstance(task_registry.beat_schedule["sample_task"]["task"], str)
    assert task_registry.beat_schedule["sample_task"]["task"].endswith("sample_task")


def test_task_factory_creates_background_task():
    task_registry = TaskRegistry()
    factory = task_registry.background_task("sample_task")(sample_task)
    background_task = factory()

    assert isinstance(background_task, BackgroundTask)
    assert isinstance(background_task.celery_task, CeleryTask)


@pytest.mark.asyncio
async def test_background_task_submit_calls_celery_apply_async(monkeypatch: MonkeyPatch):
    task_registry = TaskRegistry()
    factory = task_registry.background_task("sample_task")(sample_task)
    background_task = factory()

    mock_apply_async = MagicMock()
    monkeypatch.setattr(background_task.celery_task, "apply_async", mock_apply_async)

    input_model = InputModel(value=42)
    await background_task.submit(input_model)

    mock_apply_async.assert_called_once()
    _, kwargs = mock_apply_async.call_args
    assert kwargs["args"][0] == input_model.model_dump_json()


# Task Registry
# ----------------------------------------------------------------------------------------------------------------------


def test_task_registry_initialization():
    registry = TaskRegistry()
    assert registry.beat_schedule == {}


def test_task_registry_background_task():
    registry = TaskRegistry()
    factory = registry.background_task("sample_task", schedule=120)(sample_task)

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


# Background Task Execution
# ----------------------------------------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_task_factory_submission_executes_task(settings_fixture: Settings):
    task_registry = TaskRegistry()
    factory = task_registry.background_task("sample_task")(sample_task)
    background_task = factory()

    input_model = InputModel(value=10)
    result = background_task.celery_task(input_model.model_dump_json())
    output_model = OutputModel.model_validate_json(result)
    assert output_model.result == 10


@pytest.mark.asyncio
async def test_task_with_dependencies_execution(settings_fixture: Settings, db_fixture: DbDep):
    task_registry = TaskRegistry()
    called_current_user: list[CurrentTaskRunnerDep] = []
    called_db: list[DbDep] = []
    called_settings: list[Settings] = []

    async def sample_endpoint(
        task_input: InputModel, current_user: CurrentTaskRunnerDep, db: DbDep, settings: SettingsDep
    ) -> OutputModel:
        nonlocal called_current_user, called_db, called_settings
        called_current_user.append(current_user)
        called_db.append(db)
        called_settings.append(settings)
        return OutputModel(result=task_input.value * 2)

    async def sample_endpoint_task(task_input: InputModel, scope: WorkerScope) -> OutputModel:
        current_user = scope.to_auth_user()
        return await sample_endpoint(task_input, current_user=current_user, db=db_fixture, settings=settings_fixture)

    factory = task_registry.background_task("sample_endpoint")(sample_endpoint_task)
    background_task = factory()

    input_model = InputModel(value=5)
    result = background_task.celery_task(input_model.model_dump_json())
    output_model = OutputModel.model_validate_json(result)
    assert output_model.result == 10
    assert len(called_current_user) == 1
    assert len(called_db) == 1
    assert len(called_settings) == 1
    assert called_db[0] is db_fixture
    assert called_settings[0] is settings_fixture
