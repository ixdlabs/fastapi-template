from app.config import background
from app.config.background import background_task, periodic_task


def test_background_task_runs_async_function(monkeypatch):
    @background_task
    async def sample(a: int, b: int) -> int:
        return a + b

    result = sample(2, 3)
    assert result == 5


def test_periodic_task_registers_schedule(monkeypatch):
    background.beat_schedule.clear()

    @periodic_task(schedule=15)
    async def tick() -> None:
        return None

    assert background.beat_schedule == {tick.name: 15}
    assert tick() is None
    background.beat_schedule.clear()
