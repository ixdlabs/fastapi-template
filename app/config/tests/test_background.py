from unittest.mock import MagicMock
import asyncio
import pytest
from app.config import background
from app.config.background import shared_async_task, periodic_task
from pytest import MonkeyPatch

from app.config.settings import Settings
from app.config.celery_app import get_celery_app
from app.worker import setup_periodic_tasks


def test_background_task_runs_async_function(monkeypatch: MonkeyPatch):
    @shared_async_task
    async def sample(a: int, b: int) -> int:
        return a + b

    result = sample(2, 3)
    assert result == 5


@pytest.mark.asyncio
async def test_background_task_eager_can_run_inside_running_event_loop(monkeypatch: MonkeyPatch):
    monkeypatch.setattr("app.config.celery_app.get_settings", lambda: Settings(celery_task_always_eager=True))
    get_celery_app.cache_clear()

    @shared_async_task
    async def sample(a: int, b: int) -> int:
        await asyncio.sleep(0)
        return a + b

    assert sample.delay(2, 3).get(timeout=1) == 5


def test_periodic_task_registers_schedule(monkeypatch: MonkeyPatch):
    background.beat_schedule.clear()

    @periodic_task(schedule=15)
    async def tick() -> None:
        return None

    assert background.beat_schedule == {tick.name: 15}
    assert tick() is None
    background.beat_schedule.clear()


def test_celery_setup_periodic_tasks_registers_tasks(monkeypatch: MonkeyPatch):
    monkeypatch.setattr("app.config.settings.get_settings", lambda: Settings(celery_task_always_eager=False))
    background.beat_schedule.clear()

    @periodic_task(schedule=10)
    async def tock() -> None:
        return None

    sender = MagicMock()
    setup_periodic_tasks(sender)

    assert background.beat_schedule == {tock.name: 10}
    assert sender.add_periodic_task.called
    sender.add_periodic_task.call_args_list[0][0][1] == sender.tasks[tock.name].s()
    background.beat_schedule.clear()
