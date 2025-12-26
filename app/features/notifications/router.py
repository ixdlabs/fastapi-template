from fastapi import APIRouter

from app.features.notifications.views import notifications, crud_notifications


notification_router = APIRouter()

notification_router.include_router(notifications.router)
notification_router.include_router(crud_notifications.router)
