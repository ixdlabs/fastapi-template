from fastapi import APIRouter

from app.features.users.views import login, register, users


router = APIRouter()

router.include_router(login.router, prefix="/auth")
router.include_router(register.router, prefix="/auth")
router.include_router(users.router, prefix="/users")
