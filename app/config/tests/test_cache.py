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
