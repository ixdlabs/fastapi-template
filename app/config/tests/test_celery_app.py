from app.config.celery_app import get_celery_app


def test_celery_app_imports_task_registry():
    app = get_celery_app()
    assert "app.features.task_registry" in tuple(app.conf.imports or ())


def test_welcome_email_task_is_registered_on_celery_app():
    # Import for side effects (task registration).
    from app.features import task_registry  # noqa: F401

    app = get_celery_app()
    assert "app.features.users.tasks.welcome_email.send_welcome_email_task" in app.tasks
