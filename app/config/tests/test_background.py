from unittest.mock import MagicMock
import pytest
from app.config.background import Background, TaskRegistry, get_background
from app.config.settings import Settings
from celery import Task as CeleryTask
from pytest import MonkeyPatch


# Tests for Background
# ----------------------------------------------------------------------------------------------------------------------


def test_get_background_returns_configured_background_instance(settings_fixture: Settings):
    background = get_background(settings_fixture)
    assert isinstance(background, Background)


@pytest.mark.asyncio
async def test_submit_raises_value_error_for_non_celery_task(settings_fixture: Settings):
    bg = Background(settings_fixture)

    async def not_a_task():
        return 42

    assert await not_a_task() == 42
    with pytest.raises(ValueError, match="Function must be a Celery task"):
        await bg.submit(not_a_task)


@pytest.mark.asyncio
async def test_submit_delegates_apply_async_with_args_and_kwargs(settings_fixture: Settings, monkeypatch: MonkeyPatch):
    bg = Background(settings_fixture)

    task = MagicMock(spec=CeleryTask)
    task.apply_async = MagicMock()

    # noinspection PyTypeChecker
    await bg.submit(task, 1, 2, foo="bar")

    task.apply_async.assert_called_once_with(
        args=(1, 2),
        kwargs={"foo": "bar"},
    )


# Tests for TaskRegistry
# ----------------------------------------------------------------------------------------------------------------------


def test_background_task_runs_synchronously_when_event_loop_missing():
    registry = TaskRegistry()

    @registry.background_task("test_task")
    async def sample_task(x: int, y: int) -> int:
        return x + y

    result = sample_task(2, 3)
    assert result == 5


@pytest.mark.asyncio
async def test_background_task_runs_as_coroutine_when_event_loop_present():
    registry = TaskRegistry()

    @registry.background_task("test_task_1")
    async def sample_task(x: int, y: int) -> int:
        return x + y

    result = sample_task(4, 5)
    assert result == 9


@pytest.mark.asyncio
async def test_background_task_propagates_errors_from_wrapped_coroutine():
    registry = TaskRegistry()

    @registry.background_task("test_task_error")
    async def error_task():
        raise ValueError("Intentional error")

    with pytest.raises(ValueError, match="Intentional error"):
        error_task()


def test_background_task_with_schedule_registers_beat_entry():
    registry = TaskRegistry()

    @registry.background_task("test_task_2", schedule=120)
    async def scheduled_task():
        return 123

    assert scheduled_task() == 123
    assert "test_task_2" in registry.beat_schedule
    schedule_entry = registry.beat_schedule["test_task_2"]
    assert schedule_entry["schedule"] == 120


def test_background_task_without_schedule_skips_beat_registration():
    registry = TaskRegistry()

    @registry.background_task("test_task_3")
    async def unscheduled_task():
        return 123

    assert unscheduled_task() == 123
    assert "test_task_3" not in registry.beat_schedule


def test_include_registry_merges_beat_schedules_from_other_registry():
    registry1 = TaskRegistry()
    registry2 = TaskRegistry()

    @registry1.background_task("test_task_a", schedule=60)
    async def task_a():
        return "a"

    @registry2.background_task("test_task_b", schedule=120)
    async def task_b():
        return "b"

    registry1.include_registry(registry2)

    assert task_a() == "a"
    assert task_b() == "b"
    assert "test_task_a" in registry1.beat_schedule
    assert "test_task_b" in registry1.beat_schedule
    assert registry1.beat_schedule["test_task_a"]["schedule"] == 60
    assert registry1.beat_schedule["test_task_b"]["schedule"] == 120
