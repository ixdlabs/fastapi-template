from fastapi import APIRouter

from app.features.users.services import (
    get_me,
    login,
    refresh_tokens,
    register,
    reset_password,
    reset_password_confirm,
    change_password,
    update_users,
    delete_user,
    list_users,
    detail_user,
    verify_email_confirm,
    send_email_verification_email,
    send_password_reset_email,
)


user_router = APIRouter()
user_router.include_router(list_users.router)
user_router.include_router(detail_user.router)
user_router.include_router(update_users.router)
user_router.include_router(delete_user.router)


auth_router = APIRouter()
auth_router.include_router(login.router)
auth_router.include_router(register.router)
auth_router.include_router(get_me.router)
auth_router.include_router(refresh_tokens.router)
auth_router.include_router(verify_email_confirm.router)
auth_router.include_router(reset_password.router)
auth_router.include_router(reset_password_confirm.router)
auth_router.include_router(change_password.router)

user_task_router = APIRouter()
user_task_router.include_router(send_email_verification_email.router)
user_task_router.include_router(send_password_reset_email.router)
