import asyncio
from unittest.mock import MagicMock
import pytest
from app.config.background import Background, TaskRegistry, get_background
from app.config.settings import Settings
from celery import Task as CeleryTask
from pytest import MonkeyPatch


# Tests for Background
# ----------------------------------------------------------------------------------------------------------------------


def test_get_background_returns_background_instance(settings_fixture: Settings):
    background = get_background(settings_fixture)
    assert isinstance(background, Background)


@pytest.mark.asyncio
async def test_submit_rejects_non_celery_task(settings_fixture: Settings):
    bg = Background(settings_fixture)

    async def not_a_task():
        return 42

    assert await not_a_task() == 42
    with pytest.raises(ValueError, match="Function must be a Celery task"):
        await bg.submit(not_a_task)


@pytest.mark.asyncio
async def test_submit_calls_apply_async(settings_fixture: Settings, monkeypatch: MonkeyPatch):
    bg = Background(settings_fixture)

    task = MagicMock(spec=CeleryTask)
    task.apply_async = MagicMock()

    # noinspection PyTypeChecker
    await bg.submit(task, 1, 2, foo="bar")

    task.apply_async.assert_called_once_with(
        args=(1, 2),
        kwargs={"foo": "bar"},
    )


# Tests for shared_async_task
# ----------------------------------------------------------------------------------------------------------------------


def test_shared_async_task_no_event_loop():
    async def async_fn(x, y):
        return x + y

    registry = TaskRegistry()
    task = registry.background_task("fn1")(async_fn)
    result = task(2, 3)
    assert result == 5


@pytest.mark.asyncio
async def test_shared_async_task_with_running_loop():
    async def async_fn():
        await asyncio.sleep(0.01)
        return "ok"

    registry = TaskRegistry()
    task = registry.background_task("fn2")(async_fn)
    result = task()
    assert result == "ok"


def test_shared_async_task_exception_no_loop():
    async def async_fn():
        raise RuntimeError("boom")

    registry = TaskRegistry()
    task = registry.background_task("fn3")(async_fn)
    with pytest.raises(RuntimeError, match="boom"):
        task()


@pytest.mark.asyncio
async def test_shared_async_task_exception_with_loop():
    async def async_fn():
        raise ValueError("bad")

    registry = TaskRegistry()
    task = registry.background_task("fn4")(async_fn)
    with pytest.raises(ValueError, match="bad"):
        task()


def test_shared_async_task_returns_celery_task():
    async def async_fn():
        return 123

    registry = TaskRegistry()
    task = registry.background_task("fn5")(async_fn)
    assert isinstance(task, CeleryTask)
    assert task() == 123
