from fastapi import APIRouter

from app.features.users.views.auth import login


router = APIRouter(prefix="/users")

router.include_router(login.router)
