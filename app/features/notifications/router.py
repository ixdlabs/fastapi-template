from fastapi import APIRouter

from app.features.notifications.views import notifications


notification_router = APIRouter()

notification_router.include_router(notifications.router)
