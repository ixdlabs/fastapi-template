from fastapi import APIRouter

from app.features.preferences.services.common import list_preferences


common_preferences_router = APIRouter(prefix="/api/v1/common/preferences", tags=["Preferences"])
common_preferences_router.include_router(list_preferences.router)
