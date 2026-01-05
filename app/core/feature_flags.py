import abc
from typing import Annotated, override
from fastapi import Depends, Request
from app.core.preferences import Preferences
from app.core.settings import Settings


# Feature Flags of the client - Interface
# ----------------------------------------------------------------------------------------------------------------------


class ClientFeatureFlags(abc.ABC):
    @abc.abstractmethod
    async def supported(self, flag: str) -> bool:
        """Check if a feature flag is supported by the client."""


# Feature Flags of the server - Interface
# ----------------------------------------------------------------------------------------------------------------------
class ServerFeatureFlags(abc.ABC):
    @abc.abstractmethod
    async def enabled(self, flag: str) -> bool:
        """Check if a feature flag is enabled on the server."""


# Feature Flags combining client and server
# ----------------------------------------------------------------------------------------------------------------------


class FeatureFlags:
    def __init__(self, client_feature_flags: ClientFeatureFlags, server_feature_flags: ServerFeatureFlags):
        super().__init__()
        self.client_feature_flags = client_feature_flags
        self.server_feature_flags = server_feature_flags

    async def enabled(self, flag: str) -> bool:
        """Check if a feature flag is enabled."""
        return await self.server_feature_flags.enabled(flag)

    async def supported(self, flag: str) -> bool:
        """Check if a feature flag is supported by the client."""
        return await self.client_feature_flags.supported(flag)

    async def enabled_and_supported(self, flag: str) -> bool:
        """Check if a feature flag is both enabled and supported."""
        return await self.enabled(flag) and await self.supported(flag)


# Database-based implementations of Feature Flags on server side
# ----------------------------------------------------------------------------------------------------------------------


class DbBasedServerFeatureFlags(ServerFeatureFlags):
    def __init__(self, preferences: Preferences, settings: Settings):
        super().__init__()
        self.preferences = preferences
        self.settings = settings

    @override
    async def enabled(self, flag: str) -> bool:
        if flag in self.settings.feature_flags:
            return True
        value = await self.preferences.get(f"feature_flag.{flag}", "false")
        return value.lower() == "true"


# Header-based implementations of Feature Flags on client side
# ----------------------------------------------------------------------------------------------------------------------


class HeaderBasedClientFeatureFlags(ClientFeatureFlags):
    def __init__(self, request: Request):
        super().__init__()
        self.request = request

    @override
    async def supported(self, flag: str) -> bool:
        supported_flags = self.request.headers.get("X-Feature-Flags", "")
        return flag in [f.strip() for f in supported_flags.split(",")]


# Dependency to provide FeatureFlags instance.
# ----------------------------------------------------------------------------------------------------------------------


def get_feature_flags(request: Request, settings: Settings, preferences: Preferences) -> FeatureFlags:
    server_feature_flags = DbBasedServerFeatureFlags(preferences=preferences, settings=settings)
    client_feature_flags = HeaderBasedClientFeatureFlags(request=request)
    return FeatureFlags(client_feature_flags=client_feature_flags, server_feature_flags=server_feature_flags)


FeatureFlagsDep = Annotated[FeatureFlags, Depends(get_feature_flags)]
