from fastapi import Request
import pytest

from app.config.rate_limit import RateLimit, RateLimitExceededException, get_rate_limit_strategy
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
