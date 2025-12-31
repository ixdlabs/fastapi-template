import pytest

from fastapi.testclient import TestClient
from pytest import MonkeyPatch


@pytest.mark.asyncio
async def test_health_check_sends_ok_status_when_system_is_healthy(test_client_fixture: TestClient):
    response = test_client_fixture.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_health_check_fails_when_database_is_unreachable(
    monkeypatch: MonkeyPatch, test_client_fixture: TestClient
):
    async def mock_execute_failure(*args: object, **kwargs: object):
        raise Exception("Database unreachable")

    monkeypatch.setattr("app.core.health.DbDep.execute", mock_execute_failure)

    response = test_client_fixture.get("/health")
    assert response.status_code == 503
    assert response.json()["detail"] == "Service Unavailable"
