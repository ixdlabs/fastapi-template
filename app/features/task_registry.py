from app.config.background import celery_import_string
from app.features.users.tasks import send_email_verification_email_task, send_password_reset_email_task, echo_task

submittable_tasks = [
    celery_import_string(send_email_verification_email_task),
    celery_import_string(send_password_reset_email_task),
]

periodic_tasks = [
    {
        "echo": {
            "task": celery_import_string(echo_task),
            "schedule": 600,  # every 10 minutes
            "args": (),
        }
    }
]
