from fastapi import APIRouter

from app.features.users.views.auth import login, register


router = APIRouter(prefix="/users")

router.include_router(login.router)
router.include_router(register.router)
