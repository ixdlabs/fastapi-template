from typing import Annotated
from fastapi import Depends, Request
from app.core.preferences import Preferences
from app.core.settings import Settings


# Feature flags management class.
# ----------------------------------------------------------------------------------------------------------------------


class FeatureFlags:
    def __init__(self, request: Request, preferences: Preferences, settings: Settings):
        super().__init__()
        self.request = request
        self.preferences = preferences
        self.settings = settings

    async def enabled(self, flag: str) -> bool:
        """Check if a feature flag is enabled, first in settings then in preferences."""
        if flag in self.settings.feature_flags:
            return True
        value = await self.preferences.get(f"feature_flag.{flag}", "false")
        return value.lower() == "true"

    async def supported(self, flag: str) -> bool:
        """Check if a feature flag is supported by the client using request headers."""
        supported_flags = self.request.headers.get("X-Feature-Flags", "")
        return flag in [f.strip() for f in supported_flags.split(",")]

    async def enabled_and_supported(self, flag: str) -> bool:
        """Check if a feature flag is both enabled and supported."""
        return await self.enabled(flag) and await self.supported(flag)


# Dependency to provide FeatureFlags instance.
# ----------------------------------------------------------------------------------------------------------------------


def get_feature_flags(request: Request, settings: Settings, preferences: Preferences) -> FeatureFlags:
    return FeatureFlags(request=request, preferences=preferences, settings=settings)


FeatureFlagsDep = Annotated[FeatureFlags, Depends(get_feature_flags)]
