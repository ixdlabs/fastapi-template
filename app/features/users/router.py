from fastapi import APIRouter

from app.features.users.views import login, refresh, register, users, me, verify_email


user_router = APIRouter()
user_router.include_router(users.router)


auth_router = APIRouter()
auth_router.include_router(login.router)
auth_router.include_router(me.router)
auth_router.include_router(refresh.router)
auth_router.include_router(register.router)
auth_router.include_router(verify_email.router)
