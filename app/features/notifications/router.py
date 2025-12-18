from fastapi import APIRouter

from app.features.notifications.views import notifications


router = APIRouter(tags=["notifications"], prefix="/api/v1")

router.include_router(notifications.router, prefix="/notifications")
