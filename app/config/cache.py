from functools import lru_cache
from hashlib import md5
import logging
from typing import Annotated

from fastapi import Depends, Request
from aiocache import SimpleMemoryCache, BaseCache


logger = logging.getLogger(__name__)

# Cache class that provides get and set methods for caching.
# ----------------------------------------------------------------------------------------------------------------------


class Cache:
    def __init__(self, backend: BaseCache, request: Request):
        super().__init__()
        self.backend = backend
        self.request = request
        self.key = "cache"

    def vary(self, method: str, value: str) -> "Cache":
        """Modify the cache key to vary based on a custom method and value."""
        self.key = f"{self.key}:[{method}:{md5(value.encode()).hexdigest()}]"
        return self

    def vary_on_path(self) -> "Cache":
        """Modify the cache key to vary based on the request path."""
        return self.vary("path", self.request.url.path)

    def vary_on_auth(self) -> "Cache":
        """Modify the cache key to vary based on the Authorization header."""
        auth_header = self.request.headers.get("Authorization", "")
        return self.vary("auth", auth_header)

    def vary_on_query(self) -> "Cache":
        """Modify the cache key to vary based on the query parameters."""
        query_params = str(sorted(self.request.query_params.items()))
        return self.vary("query", query_params)

    async def set[T](self, value: T, ttl: int) -> T:
        """Set a value in the cache with the specified TTL."""
        await self.backend.set(self.key, value, ttl)  # pyright: ignore[reportUnknownMemberType]
        return value

    async def get(self) -> object:
        """Get a value from the cache."""
        return await self.backend.get(self.key)  # pyright: ignore[reportUnknownMemberType]


# Cache Backend used for caching.
# ----------------------------------------------------------------------------------------------------------------------


@lru_cache
def get_cache_backend():
    return SimpleMemoryCache()


CacheBackendDep = Annotated[BaseCache, Depends(get_cache_backend)]


# Dependency to get Cache instance for a request.
# ----------------------------------------------------------------------------------------------------------------------


def get_cache(request: Request, cache_backend: CacheBackendDep):
    return Cache(backend=cache_backend, request=request)


CacheDep = Annotated[Cache, Depends(get_cache)]
