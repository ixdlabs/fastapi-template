from fastapi import APIRouter

from app.features.users.services.common import (
    login,
    refresh_tokens,
    register,
    reset_password,
    reset_password_confirm,
    change_password,
    verify_email_confirm,
    detail_me,
    delete_me,
    login_oauth2,
    update_me,
)
from app.features.users.services.tasks import send_email_verification, send_password_reset_email
from app.features.users.services.admin import update_user, delete_user, list_users, detail_user


auth_router = APIRouter(prefix="/api/auth", tags=["Auth"])
auth_router.include_router(login_oauth2.router)
auth_router.include_router(login.router)
auth_router.include_router(register.router)
auth_router.include_router(refresh_tokens.router)
auth_router.include_router(verify_email_confirm.router)
auth_router.include_router(reset_password.router)
auth_router.include_router(reset_password_confirm.router)
auth_router.include_router(change_password.router)

admin_user_router = APIRouter(prefix="/api/v1/admin/users", tags=["Users"])
admin_user_router.include_router(list_users.router)
admin_user_router.include_router(detail_user.router)
admin_user_router.include_router(update_user.router)
admin_user_router.include_router(delete_user.router)

common_user_router = APIRouter(prefix="/api/v1/common/users", tags=["Users"])
common_user_router.include_router(detail_me.router)
common_user_router.include_router(update_me.router)
common_user_router.include_router(delete_me.router)

user_task_router = APIRouter(prefix="/api/v1/tasks/users", tags=["Users"])
user_task_router.include_router(send_email_verification.router)
user_task_router.include_router(send_password_reset_email.router)
