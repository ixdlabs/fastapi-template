from typing import Annotated
from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.cache import CacheBuilder
from app.core.settings import Settings
from app.features.preferences.models.preference import Preference


# Preferences management class with caching support.
# ----------------------------------------------------------------------------------------------------------------------


class Preferences:
    def __init__(self, settings: Settings, db: AsyncSession, cache: CacheBuilder):
        super().__init__()
        self.cache = cache.with_key("preferences").with_ttl(300).build(dict[str, str])
        self.settings = settings
        self.db = db

    async def get(self, key: str, default: str | None = None) -> str | None:
        all_preferences = await self.get_all()
        return all_preferences.get(key, default)

    async def get_all(self) -> dict[str, str]:
        if cached_value := await self.cache.get():
            return cached_value
        stmt = select(Preference)
        result = await self.db.execute(stmt)
        preferences = result.scalars().all()
        preference_map = {pref.key: pref.value for pref in preferences}
        return await self.cache.set(preference_map)


# Dependency to provide Preferences instance.
# ----------------------------------------------------------------------------------------------------------------------


def get_preferences(settings: Settings, db: AsyncSession, cache: CacheBuilder) -> Preferences:
    return Preferences(settings=settings, db=db, cache=cache)


PreferencesDep = Annotated[Preferences, Depends(get_preferences)]
