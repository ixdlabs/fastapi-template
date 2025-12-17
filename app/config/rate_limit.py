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
                headers={"X-RateLimit-Reset": str(window_stats.reset_time - time.time())},
            )


@lru_cache
def get_rate_limiter_strategy():
    backend = MemoryStorage()
    return MovingWindowRateLimiter(backend)


def get_rate_limit(request: Request):
    strategy = get_rate_limiter_strategy()
    url_key = request.url.path
    ip_key = request.client.host if request.client is not None else "unknown"
    key = f"{url_key}:{ip_key}"
    return RateLimit(key=key, strategy=strategy)


RateLimitDep = Annotated[RateLimit, Depends(get_rate_limit)]
