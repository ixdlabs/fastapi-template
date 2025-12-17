import uuid
from fastapi import FastAPI, HTTPException
import pytest

from app.config.cache import CacheDep, cached_view
from fastapi.testclient import TestClient


@pytest.fixture
def test_app():
    app = FastAPI()

    @app.get("/endpoint")
    async def endpoint():
        return {"message": str(uuid.uuid4())}

    @app.get("/cached-endpoint")
    @cached_view(ttl=60)
    async def cached_endpoint(cache: CacheDep):
        return {"message": str(uuid.uuid4())}

    @app.get("/cached-error-endpoint")
    @cached_view(ttl=60)
    async def cached_error_endpoint():
        return {"message": str(uuid.uuid4())}

    @app.get("/cached-400-endpoint")
    @cached_view(ttl=60)
    async def cached_400_endpoint(cache: CacheDep):
        raise HTTPException(status_code=400, detail=str(uuid.uuid4()))

    @app.get("/query-param-endpoint")
    @cached_view(ttl=60)
    async def query_param_endpoint(param: str, cache: CacheDep):
        return {"param": param, "message": str(uuid.uuid4())}

    @app.get("/cached-auth-based-endpoint")
    @cached_view(ttl=60, vary_on_auth=True)
    async def cached_auth_based_endpoint(cache: CacheDep):
        return {"message": str(uuid.uuid4())}

    return app


@pytest.mark.asyncio
async def test_cached_endpoint_returns_same_response(test_app: FastAPI):
    client = TestClient(test_app)

    # First request should fetch fresh data
    response = client.get("/cached-endpoint")
    assert response.status_code == 200
    first_response = response.json()
    assert "message" in first_response
    first_message = first_response["message"]

    # Subsequent requests within TTL should return cached data
    for _ in range(5):
        response = client.get("/cached-endpoint")
        assert response.status_code == 200
        cached_response = response.json()
        assert cached_response["message"] == first_message


@pytest.mark.asyncio
async def test_no_caching_on_uncached_endpoint(test_app: FastAPI):
    client = TestClient(test_app)

    messages = set()
    for i in range(10):
        response = client.get("/endpoint")
        assert response.status_code == 200
        assert "message" in response.json()

        # Each response should be unique
        messages.add(response.json()["message"])
        assert len(messages) == i + 1


def test_cachedep_is_required(test_app: FastAPI):
    client = TestClient(test_app)

    with pytest.raises(Exception) as exc_info:
        client.get("/cached-error-endpoint")
    assert "CacheDep" in str(exc_info.value)


@pytest.mark.asyncio
async def test_cache_does_not_cache_400_errors(test_app: FastAPI):
    client = TestClient(test_app)

    messages = set()
    for i in range(5):
        response = client.get("/cached-400-endpoint")
        assert response.status_code == 400
        assert "detail" in response.json()
        error_detail = response.json()["detail"]
        messages.add(error_detail)
        assert len(messages) == i + 1


@pytest.mark.asyncio
async def test_cache_keys_include_query_params(test_app: FastAPI):
    client = TestClient(test_app)

    response1 = client.get("/query-param-endpoint", params={"param": "value1"})
    assert response1.status_code == 200
    message1 = response1.json()["message"]

    response2 = client.get("/query-param-endpoint", params={"param": "value2"})
    assert response2.status_code == 200
    message2 = response2.json()["message"]

    # Ensure that different query params yield different cached responses
    assert message1 != message2
    # Re-fetch with the same params to ensure caching works
    response1_cached = client.get("/query-param-endpoint", params={"param": "value1"})
    assert response1_cached.status_code == 200
    assert response1_cached.json()["message"] == message1

    response2_cached = client.get("/query-param-endpoint", params={"param": "value2"})
    assert response2_cached.status_code == 200
    assert response2_cached.json()["message"] == message2


@pytest.mark.asyncio
async def test_cache_vary_on_auth_header(test_app: FastAPI):
    client = TestClient(test_app)

    # Request with first auth header
    headers1 = {"Authorization": "Bearer token1"}
    response1 = client.get("/cached-auth-based-endpoint", headers=headers1)
    assert response1.status_code == 200
    message1 = response1.json()["message"]
    # Re-fetch with the same auth header to ensure caching works
    response1_cached = client.get("/cached-auth-based-endpoint", headers=headers1)
    assert response1_cached.status_code == 200
    assert response1_cached.json()["message"] == message1

    # Request with second auth header
    headers2 = {"Authorization": "Bearer token2"}
    response2 = client.get("/cached-auth-based-endpoint", headers=headers2)
    assert response2.status_code == 200
    message2 = response2.json()["message"]
    # Ensure that different auth headers yield different cached responses
    assert message1 != message2
    # Re-fetch with the same second auth header to ensure caching works
    response2_cached = client.get("/cached-auth-based-endpoint", headers=headers2)
    assert response2_cached.status_code == 200
    assert response2_cached.json()["message"] == message2
