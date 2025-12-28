from pydantic import BaseModel
import pytest
from hashlib import md5
from fastapi import Request
from starlette.datastructures import Headers
from starlette.types import Scope

from aiocache import BaseCache

from app.core.cache import CacheBuilder, CacheDep, get_cache_backend, Cache, get_cache_builder


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
    return CacheBuilder(backend=cache_backend_fixture, request=request_fixture)


# Cache key behavior
# ----------------------------------------------------------------------------------------------------------------------


def test_cache_initializes_with_default_key(cache_fixture: CacheDep):
    cache_default = cache_fixture.build()
    assert cache_default.key == "cache"


def test_vary_appends_hashed_component_to_cache_key(cache_fixture: CacheDep):
    value = "example"
    expected_hash = md5(value.encode()).hexdigest()

    cache_default = cache_fixture.build()
    cache = cache_fixture.vary("custom", value).build()

    assert cache_default.key == "cache"
    assert cache.key == f"cache:[custom:{expected_hash}]"


def test_vary_on_path_uses_request_path_hash_in_key(cache_fixture: CacheDep, request_fixture: Request):
    expected_hash = md5(request_fixture.url.path.encode()).hexdigest()

    cache = cache_fixture.vary_on_path().build()
    assert cache.key == f"cache:[path:{expected_hash}]"


def test_vary_on_auth_uses_authorization_header_hash_in_key(cache_fixture: CacheDep, request_fixture: Request):
    auth_header = request_fixture.headers.get("Authorization")
    assert auth_header is not None
    expected_hash = md5(auth_header.encode()).hexdigest()

    cache = cache_fixture.vary_on_auth().build()
    assert cache.key == f"cache:[auth:{expected_hash}]"


def test_vary_on_query_uses_sorted_query_params_hash_in_key(cache_fixture: CacheDep, request_fixture: Request):
    query_str = str(sorted(request_fixture.query_params.items()))
    expected_hash = md5(query_str.encode()).hexdigest()

    cache = cache_fixture.vary_on_query().build()
    assert cache.key == f"cache:[query:{expected_hash}]"


def test_vary_chains_components_in_cache_key(cache_fixture: CacheDep, request_fixture: Request):
    path_hash = md5(request_fixture.url.path.encode()).hexdigest()
    auth_hash = md5(request_fixture.headers["Authorization"].encode()).hexdigest()

    cache = cache_fixture.vary_on_path().vary_on_auth().build()
    assert cache.key == f"cache:[path:{path_hash}]:[auth:{auth_hash}]"


# Cache get / set behavior
# ----------------------------------------------------------------------------------------------------------------------


class ExampleModel(BaseModel):
    a: int
    b: str


@pytest.mark.asyncio
async def test_set_stores_value_and_get_retrieves_it_from_backend(cache_fixture: CacheDep):
    value = ExampleModel(a=42, b="test")
    result_cache = cache_fixture.with_ttl(10).build()
    result = await result_cache.set(value)

    assert result == value
    cached_value = await result_cache.get(ExampleModel)
    assert cached_value == value


@pytest.mark.asyncio
async def test_distinct_cache_instances_do_not_collide_on_different_keys(
    cache_fixture: CacheDep, request_fixture: Request
):
    cache1 = cache_fixture.vary_on_path().with_ttl(10).build()
    cache2 = cache_fixture.vary_on_auth().with_ttl(10).build()

    _ = await cache1.set(ExampleModel(a=1, b="path-value"))
    _ = await cache2.set(ExampleModel(a=2, b="auth-value"))

    assert await cache1.get(ExampleModel) == ExampleModel(a=1, b="path-value")
    assert await cache2.get(ExampleModel) == ExampleModel(a=2, b="auth-value")


# Backend & dependency tests
# ----------------------------------------------------------------------------------------------------------------------


def test_get_cache_backend_returns_singleton_instance():
    backend1 = get_cache_backend()
    backend2 = get_cache_backend()

    assert backend1 is backend2


def test_get_cache_dependency_returns_cache_with_injected_backend_and_request(
    cache_backend_fixture: BaseCache, request_fixture: Request
):
    cache_builder = get_cache_builder(request=request_fixture, cache_backend=cache_backend_fixture)
    cache = cache_builder.build()

    assert isinstance(cache, Cache)
    assert cache.backend is cache_backend_fixture
    assert cache.key == "cache"
