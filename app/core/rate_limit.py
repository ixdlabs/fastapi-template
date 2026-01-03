"""
This module sets up a rate limiter using an in-memory storage backend
and a moving window strategy from the 'limits' library.
https://limits.readthedocs.io/en/stable/


"""

from collections.abc import Awaitable, Callable
from functools import lru_cache, wraps
from inspect import Parameter
import time
from typing import Annotated, ParamSpec, TypeVar
from fastapi import Depends, Request, status
import limits
from limits.aio.strategies import MovingWindowRateLimiter, RateLimiter
from limits import parse
from fastapi.dependencies.utils import get_typed_signature, get_typed_return_annotation

from app.core.exceptions import ServiceException
from app.core.helpers import inspect_locate_param
from app.core.settings import SettingsDep


# Rate Limiter Class that applies the rate limiting strategy.
# This will raise an HTTP 429 error if the limit is exceeded.
# ----------------------------------------------------------------------------------------------------------------------


class RateLimit:
    def __init__(self, strategy: RateLimiter, request: Request):
        super().__init__()
        self.strategy = strategy
        self.request = request

    async def limit(self, limit: str):
        """Applies the rate limit."""
        parsed_limit = parse(limit)
        allowed = await self.strategy.hit(parsed_limit, self.key())
        if not allowed:
            window_stats = await self.strategy.get_window_stats(parsed_limit, self.key())
            # https://www.ietf.org/archive/id/draft-polli-ratelimit-headers-02.html#section-3
            raise RateLimitExceededException(reset_time=int(window_stats.reset_time - time.time()))

    def key(self) -> str:
        """Generates a unique key for the request based on URL and client IP."""
        url_key = self.request.url.path
        ip_key = self.request.client.host if self.request.client is not None else "unknown"
        return f"{url_key}:{ip_key}"


# Strategy used for rate limiting.
# ----------------------------------------------------------------------------------------------------------------------


@lru_cache
def get_rate_limit_backend_from_url(rate_limit_backend_url: str):
    return limits.storage.storage_from_string(rate_limit_backend_url, implementation="redispy")


def get_rate_limit_strategy(settings: SettingsDep) -> RateLimiter:
    backend = get_rate_limit_backend_from_url(settings.rate_limit_backend_url)
    return MovingWindowRateLimiter(backend)


RateLimitStrategyDep = Annotated[RateLimiter, Depends(get_rate_limit_strategy)]

# Dependency to get the RateLimit instance for a request.
# ----------------------------------------------------------------------------------------------------------------------


def get_rate_limit(request: Request, rate_limit_strategy: RateLimitStrategyDep):
    return RateLimit(strategy=rate_limit_strategy, request=request)


RateLimitDep = Annotated[RateLimit, Depends(get_rate_limit)]


# Exceptions
# ----------------------------------------------------------------------------------------------------------------------


class RateLimitExceededException(ServiceException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    type = "rate-limit/exceeded"
    detail = "You have exceeded your rate limit"

    def __init__(self, reset_time: int):
        super().__init__(headers={"X-RateLimit-Reset": str(reset_time)})


# Decorator
# This will add a new parameter to the decorated function for RateLimit dependency injection.
# This parameter will be used to enforce rate limiting.
# ----------------------------------------------------------------------------------------------------------------------

P = ParamSpec("P")
R = TypeVar("R")


def rate_limit(limit: str):
    """
    Decorator to apply rate limiting to FastAPI route handlers.

    The decorated function must be `async`.
    The decorator should come before the HTTP method decorator (e.g., `@router.get`).
    Eg:
    ```python
    @router.get("/")
    @rate_limit("5/minute")
    async def some_route(...):
        ...
    ```
    """
    injected_rate_limit = Parameter(
        name="__rate_limit_dependency",
        annotation=RateLimitDep,
        kind=Parameter.KEYWORD_ONLY,
    )

    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        wrapped_signature = get_typed_signature(func)
        return_type = get_typed_return_annotation(func)
        wrapped_signature._return_annotation = return_type

        to_inject: list[Parameter] = []
        rate_limit_param = inspect_locate_param(wrapped_signature, injected_rate_limit, to_inject)

        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            rate_limit_instance = kwargs.pop(rate_limit_param.name, None)
            assert isinstance(rate_limit_instance, RateLimit), "RateLimit dependency injection failed"
            await rate_limit_instance.limit(limit)
            return await func(*args, **kwargs)

        # Inject the parameters to function signature
        new_params = list(wrapped_signature.parameters.values())
        new_params.extend(to_inject)

        new_signature = wrapped_signature.replace(parameters=new_params)
        setattr(wrapper, "__signature__", new_signature)

        return wrapper

    return decorator
