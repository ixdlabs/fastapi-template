from datetime import datetime, timezone
import logging
from pathlib import Path
from typing import Annotated
import uuid
from fastapi import Depends
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from fastapi import status

from app.core.background import BackgroundTask, TaskRegistry, WorkerScopeDep
from app.core.database import DbWorkerDep
from app.core.email_sender import Email, EmailSenderDep, EmailSenderWorkerDep
from app.core.exceptions import ServiceException
from app.core.settings import SettingsDep, SettingsWorkerDep
from app.features.notifications.models.notification import Notification, NotificationType
from app.features.notifications.models.notification_delivery import (
    NotificationChannel,
    NotificationDelivery,
    NotificationStatus,
)


logger = logging.getLogger(__name__)
email_templates_dir = Path(__file__).parent / "emails"

registry = TaskRegistry()


# Input/Output
# ----------------------------------------------------------------------------------------------------------------------


class SendNotificationInput(BaseModel):
    notification_id: uuid.UUID


class SendNotificationOutput(BaseModel):
    successful: list["SendNotificationOutputSuccessful"]
    failed: list["SendNotificationOutputFailed"]


class SendNotificationOutputSuccessful(BaseModel):
    delivery_id: uuid.UUID
    message_id: str


class SendNotificationOutputFailed(BaseModel):
    delivery_id: uuid.UUID
    error_message: str


# Exceptions
# ----------------------------------------------------------------------------------------------------------------------


class NotificationNotFoundException(ServiceException):
    status_code = status.HTTP_404_NOT_FOUND
    type = "notifications/tasks/send-notification/notification-not-found"
    detail = "Notification not found, it may have been deleted"


# Task implementation
# ----------------------------------------------------------------------------------------------------------------------


@registry.background_task("send_notification")
async def send_notification(
    task_input: SendNotificationInput,
    scope: WorkerScopeDep,
    settings: SettingsWorkerDep,
    db: DbWorkerDep,
    email_sender: EmailSenderWorkerDep,
) -> SendNotificationOutput:
    """
    Sends a notification to the user.
    """

    stmt = (
        select(Notification)
        .join(NotificationDelivery)
        .options(selectinload(Notification.deliveries))
        .where(Notification.id == task_input.notification_id)
        .where(NotificationDelivery.notification_id == Notification.id)
        .where(NotificationDelivery.status == NotificationStatus.PENDING)
    )
    result = await db.execute(stmt)
    notification = result.scalar_one_or_none()
    if notification is None:
        raise NotificationNotFoundException()

    # Deliver the notification via each delivery channel
    result = SendNotificationOutput(successful=[], failed=[])
    for delivery in notification.deliveries:
        try:
            message_id = await _deliver_notification(delivery, notification, settings, email_sender)
            result.successful.append(SendNotificationOutputSuccessful(delivery_id=delivery.id, message_id=message_id))
        except Exception as e:
            result.failed.append(SendNotificationOutputFailed(delivery_id=delivery.id, error_message=str(e)))

    # Update delivery statuses
    for successful in result.successful:
        _ = await db.execute(
            update(NotificationDelivery)
            .where(NotificationDelivery.id == successful.delivery_id)
            .values(
                status=NotificationStatus.SENT,
                sent_at=datetime.now(timezone.utc),
                provider_ref=successful.message_id,
            )
        )
    for failed in result.failed:
        _ = await db.execute(
            update(NotificationDelivery)
            .where(NotificationDelivery.id == failed.delivery_id)
            .values(
                status=NotificationStatus.FAILED,
                failure_message=failed.error_message,
            )
        )

    await db.commit()

    # Retry if there were failures
    logger.info("Task completed...", extra={"result": result.model_dump()})
    if result.failed:
        logger.warning("%s notifications failed to send, retrying task...", len(result.failed))
        raise scope.task.retry(exc=Exception("Some notifications failed to send"), countdown=60)

    return result


SendNotificationTaskDep = Annotated[BackgroundTask, Depends(send_notification)]


# Helpers to deliver email
# ----------------------------------------------------------------------------------------------------------------------


async def _deliver_notification(
    delivery: NotificationDelivery, notification: Notification, settings: SettingsDep, email_sender: EmailSenderDep
):
    if delivery.channel == NotificationChannel.EMAIL:
        html_template, text_template = _resolve_email_template(notification.type)
        return await email_sender.send_email(
            Email(
                sender=settings.email_sender_address,
                receivers=[delivery.recipient],
                subject=delivery.title or "Notification",
                body_html_template=html_template,
                body_text_template=text_template,
                template_data={"body": delivery.body},
            )
        )
    raise NotImplementedError(f"Delivery channel {delivery.channel} not implemented")


def _resolve_email_template(_: NotificationType) -> tuple[Path, Path]:
    return email_templates_dir / "custom_email.mjml", email_templates_dir / "custom_email.txt"
