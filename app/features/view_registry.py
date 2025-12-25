from fastapi import APIRouter

from app.features.users.views import user_task_router
from app.features.users.views import user_router
from app.features.users.views import auth_router


router = APIRouter()

router.include_router(auth_router, prefix="/api/auth", tags=["Auth"])
router.include_router(user_router, prefix="/api/v1/users", tags=["Users"])

router.include_router(user_task_router, prefix="/api/v1/tasks/users", tags=["Tasks"])
