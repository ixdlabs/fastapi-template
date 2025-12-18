import pytest
from hashlib import md5
from fastapi import Request
from starlette.datastructures import Headers
from starlette.types import Scope

from aiocache import BaseCache

from app.config.cache import CacheDep, get_cache_backend, get_cache, Cache


@pytest.fixture
def request_fixture() -> Request:
    scope: Scope = {
        "type": "http",
        "method": "GET",
        "path": "/test/path",
        "headers": Headers({"Authorization": "Bearer testtoken"}).raw,
        "query_string": b"param1=value1&param2=value2",
        "client": ("127.0.0.1", 12345),
    }
    return Request(scope)


@pytest.fixture
def cache_fixture(request_fixture: Request, cache_backend_fixture: BaseCache) -> CacheDep:
    return Cache(backend=cache_backend_fixture, request=request_fixture)


# Cache key behavior
# ----------------------------------------------------------------------------------------------------------------------


def test_default_cache_key(cache_fixture: CacheDep):
    assert cache_fixture.key == "cache"


def test_vary_adds_hashed_component(cache_fixture: CacheDep):
    value = "example"
    expected_hash = md5(value.encode()).hexdigest()

    cache_fixture.vary("custom", value)

    assert cache_fixture.key == f"cache:[custom:{expected_hash}]"


def test_vary_on_path(cache_fixture: CacheDep, request_fixture: Request):
    expected_hash = md5(request_fixture.url.path.encode()).hexdigest()

    cache_fixture.vary_on_path()

    assert cache_fixture.key == f"cache:[path:{expected_hash}]"


def test_vary_on_auth(cache_fixture: CacheDep, request_fixture: Request):
    auth_header = request_fixture.headers.get("Authorization")
    assert auth_header is not None
    expected_hash = md5(auth_header.encode()).hexdigest()

    cache_fixture.vary_on_auth()

    assert cache_fixture.key == f"cache:[auth:{expected_hash}]"


def test_vary_on_query(cache_fixture: CacheDep, request_fixture: Request):
    query_str = str(sorted(request_fixture.query_params.items()))
    expected_hash = md5(query_str.encode()).hexdigest()

    cache_fixture.vary_on_query()

    assert cache_fixture.key == f"cache:[query:{expected_hash}]"


def test_chained_vary_calls(cache_fixture: CacheDep, request_fixture: Request):
    path_hash = md5(request_fixture.url.path.encode()).hexdigest()
    auth_hash = md5(request_fixture.headers["Authorization"].encode()).hexdigest()

    cache_fixture.vary_on_path().vary_on_auth()

    assert cache_fixture.key == (f"cache:[path:{path_hash}]:[auth:{auth_hash}]")


# Cache get / set behavior
# ----------------------------------------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_set_and_get_value(cache_fixture: CacheDep):
    value = {"a": 1}
    ttl = 10

    result = await cache_fixture.set(value, ttl)

    assert result == value
    cached_value = await cache_fixture.get()
    assert cached_value == value


@pytest.mark.asyncio
async def test_different_keys_do_not_collide(cache_backend_fixture: BaseCache, request_fixture: Request):
    cache1 = Cache(backend=cache_backend_fixture, request=request_fixture).vary_on_path()
    cache2 = Cache(backend=cache_backend_fixture, request=request_fixture).vary_on_auth()

    await cache1.set("path-value", ttl=10)
    await cache2.set("auth-value", ttl=10)

    assert await cache1.get() == "path-value"
    assert await cache2.get() == "auth-value"


# Backend & dependency tests
# ----------------------------------------------------------------------------------------------------------------------


def test_get_cache_backend_is_singleton():
    backend1 = get_cache_backend()
    backend2 = get_cache_backend()

    assert backend1 is backend2


def test_get_cache_dependency_returns_cache_instance(cache_backend_fixture: BaseCache, request_fixture: Request):
    cache = get_cache(request=request_fixture, cache_backend=cache_backend_fixture)

    assert isinstance(cache, Cache)
    assert cache.backend is cache_backend_fixture
    assert cache.request is request_fixture
    assert cache.key == "cache"
