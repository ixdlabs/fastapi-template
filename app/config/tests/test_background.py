from unittest.mock import MagicMock
from app.config import background
from app.config.background import background_task, periodic_task
from pytest import MonkeyPatch

from app.config.settings import Settings
from app.worker import setup_periodic_tasks


def test_background_task_runs_async_function(monkeypatch: MonkeyPatch):
    @background_task
    async def sample(a: int, b: int) -> int:
        return a + b

    result = sample(2, 3)
    assert result == 5


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
