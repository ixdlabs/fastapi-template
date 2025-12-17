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


# Rate Limiter Class that applies the rate limiting strategy.
# This will raise an HTTP 429 error if the limit is exceeded.
# ----------------------------------------------------------------------------------------------------------------------


class RateLimit:
    def __init__(self, strategy: RateLimiter, request: Request):
        self.strategy = strategy
        self.request = request

    async def limit(self, limit: str):
        """Applies the rate limit."""
        parsed_limit = parse(limit)
        allowed = await self.strategy.hit(parsed_limit, self.key())
        if not allowed:
            window_stats = await self.strategy.get_window_stats(parsed_limit, self.key())
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too Many Requests",
                # https://www.ietf.org/archive/id/draft-polli-ratelimit-headers-02.html#section-3
                headers={"X-RateLimit-Reset": str(int(window_stats.reset_time - time.time()))},
            )

    def key(self) -> str:
        url_key = self.request.url.path
        ip_key = self.request.client.host if self.request.client is not None else "unknown"
        return f"{url_key}:{ip_key}"


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
    return RateLimit(strategy=rate_limit_strategy, request=request)


RateLimitDep = Annotated[RateLimit, Depends(get_rate_limit)]
