from fastapi import APIRouter

from app.features.users.router import user_router
from app.features.users.router import auth_router

from app.features.notifications.router import notification_router


router = APIRouter()

router.include_router(auth_router, prefix="/api/auth", tags=["Auth"])
router.include_router(user_router, prefix="/api/v1/users", tags=["Users"])
router.include_router(notification_router, prefix="/api/v1/notifications", tags=["Notifications"])
