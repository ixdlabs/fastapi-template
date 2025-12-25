from fastapi import APIRouter

from app.features.users.views import (
    crud_users,
    get_me,
    login,
    refresh_tokens,
    register,
    reset_password,
    reset_password_confirm,
    change_password,
    verify_email_confirm,
)


user_router = APIRouter()
user_router.include_router(crud_users.router)


auth_router = APIRouter()
auth_router.include_router(login.router)
auth_router.include_router(register.router)
auth_router.include_router(get_me.router)
auth_router.include_router(refresh_tokens.router)
auth_router.include_router(verify_email_confirm.router)
auth_router.include_router(reset_password.router)
auth_router.include_router(reset_password_confirm.router)
auth_router.include_router(change_password.router)
