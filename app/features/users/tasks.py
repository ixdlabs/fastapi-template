import logging

from app.core.background import TaskRegistry

from app.features.users.services.tasks import send_email_verification, send_password_reset_email


logger = logging.getLogger(__name__)
user_registry = TaskRegistry()
user_registry.include_registry(send_email_verification.registry)
user_registry.include_registry(send_password_reset_email.registry)
