from fastapi import APIRouter

from app.features.users.views import login, refresh, register, users


user_router = APIRouter()
user_router.include_router(users.router)


auth_router = APIRouter()
auth_router.include_router(login.router)
auth_router.include_router(register.router)
auth_router.include_router(refresh.router)
