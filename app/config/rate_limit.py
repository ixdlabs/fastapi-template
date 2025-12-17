"""
This module sets up a rate limiter using an in-memory storage backend
and a moving window strategy from the 'limits' library.
https://limits.readthedocs.io/en/stable/


"""

from functools import lru_cache
import time
from typing import Annotated
from fastapi import Depends, HTTPException, Request, status
from limits.aio.storage import MemoryStorage
from limits.aio.strategies import MovingWindowRateLimiter, RateLimiter
from limits import parse


# Helper function to build a unique rate limit key based on request URL and client IP.
# ----------------------------------------------------------------------------------------------------------------------


def build_client_identification_key(request: Request) -> str:
    url_key = request.url.path
    ip_key = request.client.host if request.client is not None else "unknown"
    return f"{url_key}:{ip_key}"


# Rate Limiter Class that applies the rate limiting strategy.
# This will raise an HTTP 429 error if the limit is exceeded.
# ----------------------------------------------------------------------------------------------------------------------


class RateLimit:
    def __init__(self, key: str, strategy: RateLimiter):
        self.key = key
        self.strategy = strategy

    async def limit(self, limit: str):
        """Applies the rate limit."""
        parsed_limit = parse(limit)
        allowed = await self.strategy.hit(parsed_limit, self.key)
        if not allowed:
            window_stats = await self.strategy.get_window_stats(parsed_limit, self.key)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too Many Requests",
                # https://www.ietf.org/archive/id/draft-polli-ratelimit-headers-02.html#section-3
                headers={"X-RateLimit-Reset": str(int(window_stats.reset_time - time.time()))},
            )

    async def reset(self):
        """Clears the rate limit for the key."""
        await self.strategy.storage.clear(self.key)


# Strategy used for rate limiting.
# ----------------------------------------------------------------------------------------------------------------------


@lru_cache
def get_rate_limit_strategy():
    backend = MemoryStorage()
    return MovingWindowRateLimiter(backend)


RateLimitStrategyDep = Annotated[RateLimiter, Depends(get_rate_limit_strategy)]

# Dependency to get the RateLimit instance for a request.
# ----------------------------------------------------------------------------------------------------------------------


def get_rate_limit(request: Request, rate_limit_strategy: RateLimitStrategyDep):
    key = build_client_identification_key(request)
    return RateLimit(key=key, strategy=rate_limit_strategy)


RateLimitDep = Annotated[RateLimit, Depends(get_rate_limit)]
