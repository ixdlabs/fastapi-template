from fastapi import APIRouter

from app.features.users.views import login, register, users


router = APIRouter(tags=["users"], prefix="/api/v1")

router.include_router(login.router, prefix="/auth")
router.include_router(register.router, prefix="/auth")
router.include_router(users.router, prefix="/users")
