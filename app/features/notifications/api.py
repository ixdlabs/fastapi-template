from fastapi import APIRouter

from app.features.notifications.services.common import (
    get_notification_summary,
    list_notifications,
    read_all_notifications,
    unread_notification,
    read_notification,
    detail_notification,
)


common_notification_router = APIRouter(prefix="/api/v1/common/notifications", tags=["Notifications"])
common_notification_router.include_router(get_notification_summary.router)
common_notification_router.include_router(list_notifications.router)
common_notification_router.include_router(detail_notification.router)
common_notification_router.include_router(read_notification.router)
common_notification_router.include_router(unread_notification.router)
common_notification_router.include_router(read_all_notifications.router)
