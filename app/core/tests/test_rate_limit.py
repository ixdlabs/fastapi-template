from inspect import Parameter, Signature, signature
from fastapi import APIRouter, Request
from limits import parse
import pytest

from app.core.rate_limit import (
    RateLimit,
    RateLimitDep,
    RateLimitExceededException,
    get_rate_limit,
    get_rate_limit_strategy,
    rate_limit,
)
import time_machine


def make_request(path: str = "/test", client_host: str | None = "127.0.0.1") -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": path,
            "raw_path": path.encode(),
            "headers": [],
            "query_string": b"",
            "scheme": "http",
            "server": ("testserver", 80),
            "client": (client_host, 12345) if client_host else None,
        }
    )


# Key generation
# ----------------------------------------------------------------------------------------------------------------------


def test_rate_limit_key_includes_path_and_client_ip_when_present():
    request = make_request("/api/resource", "10.0.0.1")
    strategy = get_rate_limit_strategy()

    rate_limit = RateLimit(strategy=strategy, request=request)

    assert rate_limit.key() == "/api/resource:10.0.0.1"


def test_rate_limit_key_defaults_to_unknown_when_client_missing():
    request = make_request("/api/resource", None)
    strategy = get_rate_limit_strategy()

    rate_limit = RateLimit(strategy=strategy, request=request)

    assert rate_limit.key() == "/api/resource:unknown"


# Rate limiting with time_machine
# ----------------------------------------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rate_limit_allows_first_request_within_window():
    with time_machine.travel("2025-01-01 00:00:00"):
        request = make_request()
        strategy = get_rate_limit_strategy()
        rate_limit = RateLimit(strategy=strategy, request=request)

        # Should not raise
        await rate_limit.limit("1/minute")


@pytest.mark.asyncio
async def test_rate_limit_blocks_second_request_in_same_window_and_returns_headers():
    with time_machine.travel("2025-01-01 00:00:00"):
        request = make_request()
        strategy = get_rate_limit_strategy()
        rate_limit = RateLimit(strategy=strategy, request=request)

        # First hit is allowed
        await rate_limit.limit("1/minute")
        # Second hit in same window should fail
        with pytest.raises(RateLimitExceededException) as exc:
            await rate_limit.limit("1/minute")

        exception = exc.value
        assert exception.status_code == 429
        assert exception.detail == "You have exceeded your rate limit"
        assert exception.headers is not None
        assert "X-RateLimit-Reset" in exception.headers


@pytest.mark.asyncio
async def test_rate_limit_allows_request_after_window_resets():
    with time_machine.travel("2025-01-01 00:00:00"):
        request = make_request()
        strategy = get_rate_limit_strategy()
        rate_limit = RateLimit(strategy=strategy, request=request)

        # First request
        await rate_limit.limit("1/minute")
        # Second request blocked
        with pytest.raises(RateLimitExceededException):
            await rate_limit.limit("1/minute")

    with time_machine.travel("2025-01-01 00:01:01"):
        # Should be allowed again after window
        await rate_limit.limit("1/minute")


@pytest.mark.asyncio
async def test_rate_limit_sets_reset_header_within_window_bounds():
    with time_machine.travel("2025-01-01 00:00:00"):
        request = make_request()
        strategy = get_rate_limit_strategy()
        rate_limit = RateLimit(strategy=strategy, request=request)

        await rate_limit.limit("1/minute")

        with pytest.raises(RateLimitExceededException) as exc:
            await rate_limit.limit("1/minute")

        assert exc.value.headers is not None
        assert "X-RateLimit-Reset" in exc.value.headers
        reset = int(exc.value.headers["X-RateLimit-Reset"])
        assert 0 < reset <= 60


# Tests for decorator
# ----------------------------------------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rate_limit_decorator_adds_dependency_parameter():
    router = APIRouter()

    async def test_endpoint(param1: int):
        return {"param1": param1}

    assert await test_endpoint(1) == {"param1": 1}
    rl_endpoint = router.get("/test")(rate_limit("5/minute")(test_endpoint))

    sig = signature(rl_endpoint)
    params = list(sig.parameters.values())

    assert any(param.annotation == RateLimitDep for param in params)


@pytest.mark.asyncio
async def test_rate_limit_reuses_existing_dependency_param():
    dep_param = Parameter(
        name="rate_limit",
        annotation=RateLimitDep,
        kind=Parameter.KEYWORD_ONLY,
    )

    sig = Signature(parameters=[dep_param])

    async def handler():
        return "ok"

    assert await handler() == "ok"
    setattr(handler, "__signature__", sig)
    wrapped = rate_limit("10/second")(handler)

    wrapped_signature = getattr(wrapped, "__signature__")
    assert isinstance(wrapped_signature, Signature)
    params = wrapped_signature.parameters
    assert "rate_limit" in params
    assert "__rate_limit_dependency" not in params


@pytest.mark.asyncio
async def test_rate_limit_calls_limit():
    request = make_request()
    strategy = get_rate_limit_strategy()
    rate_limit_obj = RateLimit(strategy=strategy, request=request)

    async def handler(x: int):
        return "ok"

    assert await handler(x=1) == "ok"
    rl_handler = rate_limit("3/minute")(handler)

    result = await rl_handler(x=1, __rate_limit_dependency=rate_limit_obj)  # pyright: ignore[reportCallIssue]

    assert result == "ok"
    parsed_limit = parse("3/minute")
    stats = await rate_limit_obj.strategy.get_window_stats(parsed_limit, rate_limit_obj.key())
    assert stats.remaining == 2


@pytest.mark.asyncio
async def test_rate_limit_strips_dependency_kwarg():
    request = make_request()
    strategy = get_rate_limit_strategy()
    limiter = RateLimit(strategy=strategy, request=request)

    async def handler():
        return "ok"

    assert await handler() == "ok"
    rl_handler = rate_limit("1/second")(handler)

    result = await rl_handler(__rate_limit_dependency=limiter)  # pyright: ignore[reportCallIssue]
    assert result == "ok"


@pytest.mark.asyncio
async def test_rate_limit_raises_when_dependency_missing():
    async def handler():
        return "ok"

    assert await handler() == "ok"
    rl_handler = rate_limit("5/minute")(handler)

    with pytest.raises(AssertionError, match="RateLimit dependency injection failed"):
        _ = await rl_handler()


# Tests for get_rate_limit
# ----------------------------------------------------------------------------------------------------------------------


def test_get_rate_limit_returns_rate_limit_instance():
    request = make_request()
    strategy = get_rate_limit_strategy()

    rate_limit = get_rate_limit(request, strategy)
    assert isinstance(rate_limit, RateLimit)
