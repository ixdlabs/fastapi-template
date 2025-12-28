from functools import lru_cache
from hashlib import md5
import logging
from typing import Annotated, TypeVar

from fastapi import Depends, Request
from aiocache import SimpleMemoryCache, BaseCache
from pydantic import BaseModel, ValidationError


logger = logging.getLogger(__name__)

# Cache class that provides get and set methods for caching.
# ----------------------------------------------------------------------------------------------------------------------


T = TypeVar("T", bound=BaseModel)


class Cache:
    def __init__(self, *, backend: BaseCache, key: str, ttl: int):
        super().__init__()
        self.backend = backend
        self.key = key
        self.ttl = ttl

    async def set(self, value: T) -> T:
        """Set a value in the cache with the specified TTL."""
        persist_value = value.model_dump_json()
        await self.backend.set(self.key, persist_value, self.ttl)  # pyright: ignore[reportUnknownMemberType]
        return value

    async def get(self, cls: type[T]) -> T | None:
        """Get a value from the cache."""
        persist_value = await self.backend.get(self.key)  # pyright: ignore[reportUnknownMemberType]
        if persist_value is None:
            return None

        try:
            return cls.model_validate_json(persist_value)
        except ValidationError as e:
            logger.warning("Cache hit but failed to validate cached data", exc_info=e)
            return None


class CacheBuilder:
    def __init__(self, *, backend: BaseCache, request: Request, key: str = "cache", ttl: int = 300):
        super().__init__()
        self._backend = backend
        self._request = request
        self._key = key
        self._ttl = ttl

    def vary(self, method: str, value: str) -> "CacheBuilder":
        """Modify the cache key to vary based on a custom method and value."""
        hashed = md5(value.encode()).hexdigest()
        return self.with_key(f"{self._key}:[{method}:{hashed}]")

    def vary_on_path(self) -> "CacheBuilder":
        """Modify the cache key to vary based on the request path."""
        return self.vary("path", self._request.url.path)

    def vary_on_auth(self) -> "CacheBuilder":
        """Modify the cache key to vary based on the Authorization header."""
        auth_header = self._request.headers.get("Authorization", "")
        return self.vary("auth", auth_header)

    def vary_on_query(self) -> "CacheBuilder":
        """Modify the cache key to vary based on the query parameters."""
        query_params = str(sorted(self._request.query_params.items()))
        return self.vary("query", query_params)

    def with_ttl(self, ttl: int) -> "CacheBuilder":
        """Set a custom TTL for the cache."""
        return CacheBuilder(backend=self._backend, request=self._request, key=self._key, ttl=ttl)

    def with_key(self, key: str) -> "CacheBuilder":
        """Set a custom cache key."""
        return CacheBuilder(backend=self._backend, request=self._request, key=key, ttl=self._ttl)

    def build(self) -> Cache:
        """Build the Cache instance."""
        return Cache(backend=self._backend, key=self._key, ttl=self._ttl)


# Cache Backend used for caching.
# ----------------------------------------------------------------------------------------------------------------------


@lru_cache
def get_cache_backend():
    return SimpleMemoryCache()


CacheBackendDep = Annotated[BaseCache, Depends(get_cache_backend)]


# Dependency to get Cache instance for a request.
# ----------------------------------------------------------------------------------------------------------------------


def get_cache_builder(request: Request, cache_backend: CacheBackendDep):
    return CacheBuilder(backend=cache_backend, request=request)


CacheDep = Annotated[CacheBuilder, Depends(get_cache_builder)]
