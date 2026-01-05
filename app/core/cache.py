from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
import logging
from typing import Annotated

from fastapi import Depends, Request
from aiocache import BaseCache, Cache as AioCache
from pydantic import BaseModel, ValidationError

from app.core.auth import AuthException, Authenticator, AuthenticatorDep
from app.core.settings import SettingsDep


logger = logging.getLogger(__name__)


class CachableContainer[DataT](BaseModel):
    """Container model to wrap cached data for validation."""

    value: DataT


# Cache class that provides get and set methods for caching.
# ----------------------------------------------------------------------------------------------------------------------


class Cache[T]:
    def __init__(self, *, backend: BaseCache, value_cls: type[T], key: str, ttl: int):
        super().__init__()
        self.backend = backend
        self.value_cls = value_cls
        self.key = key
        self.ttl = ttl

    async def set(self, value: T) -> T:
        """Set a value in the cache with the specified TTL."""
        cache_value = CachableContainer(value=value)
        persist_value = cache_value.model_dump_json()
        hashed_key = sha256(self.key.encode()).hexdigest()
        await self.backend.set(hashed_key, persist_value, self.ttl)  # pyright: ignore[reportUnknownMemberType]
        logger.info("Cached value under key %s for %d seconds", self.key, self.ttl)
        return value

    async def get(self) -> T | None:
        """Get a value from the cache."""
        logger.info("Fetching cached value under key %s", self.key)
        hashed_key = sha256(self.key.encode()).hexdigest()
        persist_value = await self.backend.get(hashed_key)  # pyright: ignore[reportUnknownMemberType]
        if persist_value is None:
            return None

        try:
            cached_value = CachableContainer[self.value_cls].model_validate_json(persist_value)
            return cached_value.value
        except ValidationError as e:
            logger.warning("Cache hit but failed to validate cached data", exc_info=e)
            return None


# Cache Builder to create Cache instances with varying keys and TTLs.
# ----------------------------------------------------------------------------------------------------------------------


@dataclass
class CacheBuilderState:
    key: str
    ttl: int


class CacheBuilder:
    def __init__(self, *, backend: BaseCache, request: Request, authenticator: Authenticator):
        super().__init__()
        self.backend = backend
        self.request = request
        self.authenticator = authenticator
        self.state = CacheBuilderState(key="cache", ttl=300)

    def vary(self, method: str, value: str) -> "CacheBuilder":
        """Modify the cache key to vary based on a custom method and value."""
        return self.with_key(f"{self.state.key}:[{method}:{value}]")

    def vary_on_path(self) -> "CacheBuilder":
        """Modify the cache key to vary based on the request path."""
        return self.vary("path", self.request.url.path)

    def vary_on_auth(self) -> "CacheBuilder":
        """Modify the cache key to vary based on the Authorization header."""
        try:
            access_token = self.authenticator.access_token_from_headers(self.request.headers)
            user_id = self.authenticator.sub(access_token)
            return self.vary("auth", str(user_id))
        except AuthException:
            return self.vary("auth", "anonymous")

    def vary_on_query(self) -> "CacheBuilder":
        """Modify the cache key to vary based on the query parameters."""
        items = sorted(self.request.query_params.items())
        canonical = "&".join(f"{k}={v}" for k, v in items)
        return self.vary("query", canonical)

    def with_ttl(self, ttl: int) -> "CacheBuilder":
        """Set a custom TTL for the cache."""
        self.state = CacheBuilderState(key=self.state.key, ttl=ttl)
        return self

    def with_key(self, key: str) -> "CacheBuilder":
        """Set a custom cache key."""
        self.state = CacheBuilderState(key=key, ttl=self.state.ttl)
        return self

    def build[T](self, cls: type[T]) -> Cache[T]:
        """Build the Cache instance."""
        return Cache[T](backend=self.backend, value_cls=cls, key=self.state.key, ttl=self.state.ttl)


# Cache Backend used for caching.
# ----------------------------------------------------------------------------------------------------------------------


@lru_cache
def get_cache_backend_from_url(cache_url: str):
    return AioCache.from_url(cache_url)  # pyright: ignore[reportUnknownMemberType]


def get_cache_backend(settings: SettingsDep):
    return get_cache_backend_from_url(settings.cache_url)


CacheBackendDep = Annotated[BaseCache, Depends(get_cache_backend)]


# Dependency to get Cache instance for a request.
# ----------------------------------------------------------------------------------------------------------------------


def get_cache_builder(request: Request, authenticator: AuthenticatorDep, backend: CacheBackendDep) -> CacheBuilder:
    return CacheBuilder(backend=backend, request=request, authenticator=authenticator)


CacheDep = Annotated[CacheBuilder, Depends(get_cache_builder)]
