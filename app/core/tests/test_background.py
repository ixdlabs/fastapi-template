from unittest.mock import MagicMock
from pydantic import BaseModel
import pytest
from app.core.background import BackgroundTask, TaskRegistry
from app.core.settings import Settings


class InputModel(BaseModel):
    value: int


class OutputModel(BaseModel):
    result: int


async def sample_task(task_input: InputModel, **kwargs: object) -> OutputModel:
    return OutputModel(result=task_input.value)


# Background Tasks
# ----------------------------------------------------------------------------------------------------------------------


def test_register_background_task_returns_factory(task_registry_fixture: TaskRegistry):
    factory = task_registry_fixture.register_background_task(sample_task)
    assert callable(factory)


def test_register_background_task_adds_beat_schedule(task_registry_fixture: TaskRegistry):
    _ = task_registry_fixture.register_background_task(sample_task, schedule=60)

    assert "sample_task" in task_registry_fixture.beat_schedule
    assert task_registry_fixture.beat_schedule["sample_task"]["schedule"] == 60
    assert isinstance(task_registry_fixture.beat_schedule["sample_task"]["task"], str)
    assert task_registry_fixture.beat_schedule["sample_task"]["task"].endswith("sample_task")


def test_task_factory_creates_background_task(
    celery_background_fixture: MagicMock, task_registry_fixture: TaskRegistry, settings_fixture: Settings
):
    factory = task_registry_fixture.register_background_task(sample_task)
    background_task = factory(settings_fixture)

    assert isinstance(background_task, BackgroundTask)
    assert background_task.celery_task is celery_background_fixture
    assert background_task.settings is settings_fixture


@pytest.mark.asyncio
async def test_background_task_submit_calls_celery_apply_async(
    celery_background_fixture: MagicMock, task_registry_fixture: TaskRegistry, settings_fixture: Settings
):
    factory = task_registry_fixture.register_background_task(sample_task)
    background_task = factory(settings_fixture)

    input_model = InputModel(value=42)
    await background_task.submit(input_model)

    celery_background_fixture.apply_async.assert_called_once()
    _, kwargs = celery_background_fixture.apply_async.call_args
    assert kwargs == {"args": (input_model.model_dump_json(),)}


# Task Registry
# ----------------------------------------------------------------------------------------------------------------------


def test_task_registry_initialization():
    registry = TaskRegistry()
    assert registry.beat_schedule == {}
    assert callable(registry.worker_get_settings)
    assert callable(registry.worker_get_db_session)


def test_task_registry_register_background_task():
    registry = TaskRegistry()
    factory = registry.register_background_task(sample_task, schedule=120)

    assert callable(factory)
    assert "sample_task" in registry.beat_schedule
    assert registry.beat_schedule["sample_task"]["schedule"] == 120
    assert isinstance(registry.beat_schedule["sample_task"]["task"], str)
    assert registry.beat_schedule["sample_task"]["task"].endswith("sample_task")


def test_task_registry_register_background_task_without_schedule():
    registry = TaskRegistry()
    factory = registry.register_background_task(sample_task)

    assert callable(factory)
    assert "sample_task" not in registry.beat_schedule


# Background Task Execution
# ----------------------------------------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_task_factory_submission_executes_task(task_registry_fixture: TaskRegistry, settings_fixture: Settings):
    factory = task_registry_fixture.register_background_task(sample_task)
    background_task = factory(settings_fixture)

    input_model = InputModel(value=10)
    result = background_task.celery_task(input_model.model_dump_json())
    output_model = OutputModel.model_validate_json(result)
    assert output_model.result == 10
