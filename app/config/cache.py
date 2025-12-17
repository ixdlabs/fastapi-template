from functools import lru_cache, wraps
from hashlib import md5
import logging
from typing import Annotated, Callable

from fastapi import Depends, Request
from aiocache import SimpleMemoryCache, BaseCache


logger = logging.getLogger(__name__)

# Decorator to cache the result of a view function.
# To use, add the `CacheDep` dependency to the endpoint and decorate the function with `@cached_view`.
# ----------------------------------------------------------------------------------------------------------------------


def cached_view(ttl: int, vary_on_auth: bool = False):
    """Decorator to cache the result of a view function."""

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache = kwargs.get("cache")
            if cache is None:
                raise Exception("Cache dependency not provided, include CacheDep in the endpoint dependencies.")
            assert isinstance(cache, Cache)

            if vary_on_auth:
                cache.vary_on_auth()

            cached_result = await cache.get()
            if cached_result is not None:
                return cached_result

            result = await func(*args, **kwargs)
            await cache.set(result, ttl)
            return result

        return wrapper

    return decorator


# Cache class that provides get and set methods for caching.
# ----------------------------------------------------------------------------------------------------------------------


class Cache:
    def __init__(self, backend: BaseCache, request: Request):
        self.backend = backend
        self.request = request
        self.prefix = "cache"

    def add_prefix(self, prefix: str):
        self.prefix = f"{self.prefix}:[{prefix}]"

    def vary_on_auth(self):
        auth_header = self.request.headers.get("Authorization", "")
        self.add_prefix(f"auth:{md5(auth_header.encode()).hexdigest()}")

    def key(self) -> str:
        query_params = str(sorted(self.request.query_params.items()))
        return f"{self.prefix}:{self.request.url.path}?{query_params}"

    def set(self, value, ttl: int):
        return self.backend.set(self.key(), value, ttl)

    def get(self):
        return self.backend.get(self.key())


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
