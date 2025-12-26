from fastapi import APIRouter

from app.features.users.api import user_task_router
from app.features.users.api import admin_user_router
from app.features.users.api import common_user_router
from app.features.users.api import auth_router

from app.features.notifications.router import notification_router


router = APIRouter()

router.include_router(auth_router)
router.include_router(admin_user_router)
router.include_router(common_user_router)
router.include_router(user_task_router)
router.include_router(notification_router)
