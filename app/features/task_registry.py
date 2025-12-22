from dataclasses import dataclass
from datetime import timedelta
from celery.schedules import crontab
from app.features.users.tasks.welcome_email import send_welcome_email_task
from app.features.users.tasks.echo import echo_task


@dataclass
class PeriodicTask:
    name: str
    task: str
    schedule: int | crontab | timedelta
    args: tuple


# Define periodic task schedule here.
# ----------------------------------------------------------------------------------------------------------------------

periodic_tasks = [
    PeriodicTask(
        name="echo-every-10-seconds",
        task="app.features.users.tasks.echo.echo_task",
        schedule=timedelta(seconds=10),
        args=("Hello, World!",),
    ),
]


# Build the schedule dictionary for Celery Beat.
# ----------------------------------------------------------------------------------------------------------------------


__all__ = [
    "send_welcome_email_task",
    "echo_task",
]
