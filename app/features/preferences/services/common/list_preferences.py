import uuid
from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from app.core.cache import CacheDep
from app.core.database import DbDep
from app.features.preferences.models.preference import Preference


router = APIRouter()

# Input/Output
# ----------------------------------------------------------------------------------------------------------------------


class PreferenceListOutput(BaseModel):
    id: uuid.UUID
    key: str
    value: str


# Preference list endpoint
# ----------------------------------------------------------------------------------------------------------------------


@router.get("/")
async def list_preferences(db: DbDep, cache: CacheDep) -> list[PreferenceListOutput]:
    """
    List the preferences that are marked as global in the system.
    This endpoint is cached since preferences change infrequently.
    """
    # Check and return from cache
    preference_cache = cache.vary_on_path().with_ttl(60).build(list[PreferenceListOutput])
    if cache_result := await preference_cache.get():
        return cache_result

    # Build query with filters
    stmt = select(Preference).filter(Preference.is_global.is_(True))
    result = await db.execute(stmt)
    preferences = result.scalars().all()

    return await preference_cache.set(
        [
            PreferenceListOutput(
                id=pref.id,
                key=pref.key,
                value=pref.value,
            )
            for pref in preferences
        ]
    )
