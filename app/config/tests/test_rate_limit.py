from datetime import datetime, timedelta
from fastapi import FastAPI
import pytest

from app.config.rate_limit import RateLimitDep
from fastapi.testclient import TestClient
import time_machine


@pytest.fixture
def test_app():
    app = FastAPI()

    @app.get("/endpoint")
    async def endpoint():
        return {"message": "Success"}

    @app.get("/ratelimit-endpoint")
    async def ratelimit_endpoint(rate_limit: RateLimitDep):
        await rate_limit.limit("5/minute")
        return {"message": "Success"}

    return app


@pytest.mark.asyncio
async def test_rate_limiting(test_app: FastAPI):
    current_time = datetime.now()
    with time_machine.travel(current_time):
        client = TestClient(test_app)

        # Make 5 allowed requests - 6th request should be rate limited
        for _ in range(5):
            response = client.get("/ratelimit-endpoint")
            assert response.status_code == 200
            assert response.json() == {"message": "Success"}

        response = client.get("/ratelimit-endpoint")
        assert response.status_code == 429
        assert response.json()["detail"] == "Too Many Requests"
        assert "X-RateLimit-Reset" in response.headers
        reset_time = int(response.headers["X-RateLimit-Reset"])
        assert reset_time > 0

    # Wait for more than a minute to reset the rate limit
    with time_machine.travel(current_time + timedelta(minutes=1, seconds=1)):
        response = client.get("/ratelimit-endpoint")
        assert response.status_code == 200
        assert response.json() == {"message": "Success"}


@pytest.mark.asyncio
async def test_no_rate_limiting_on_unprotected_endpoint(test_app: FastAPI):
    client = TestClient(test_app)

    for _ in range(10):
        response = client.get("/endpoint")
        assert response.status_code == 200
        assert response.json() == {"message": "Success"}
