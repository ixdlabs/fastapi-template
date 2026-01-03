import pytest

from fastapi.testclient import TestClient
from pytest import MonkeyPatch


@pytest.mark.asyncio
async def test_health_liveliness_check_sends_ok_status_when_system_is_healthy(test_client_fixture: TestClient):
    response = test_client_fixture.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_health_readiness_check_sends_ok_status_when_system_is_healthy(test_client_fixture: TestClient):
    response = test_client_fixture.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert "last_check" in response.json()


@pytest.mark.asyncio
async def test_health_readiness_check_fails_when_database_is_unreachable(
    monkeypatch: MonkeyPatch, test_client_fixture: TestClient
):
    async def mock_execute_failure(*args: object, **kwargs: object):
        raise Exception("Database unreachable")

    monkeypatch.setattr("app.core.health.DbDep.execute", mock_execute_failure)

    response = test_client_fixture.get("/health/ready")
    assert response.status_code == 503
    assert response.json()["detail"] == "Database service is unavailable"


@pytest.mark.asyncio
async def test_health_readiness_check_fails_when_celery_is_unreachable(
    monkeypatch: MonkeyPatch, test_client_fixture: TestClient
):
    def mock_control_ping_failure(*args: object, **kwargs: object) -> list[object]:
        return []

    monkeypatch.setattr("app.core.health.current_app.conf.task_always_eager", False)
    monkeypatch.setattr("app.core.health.current_app.control.ping", mock_control_ping_failure)

    response = test_client_fixture.get("/health/ready")
    assert response.status_code == 503
    assert response.json()["detail"] == "Background workers are unavailable"


@pytest.mark.asyncio
async def test_health_readiness_check_succeeds_when_celery_is_eager(
    monkeypatch: MonkeyPatch, test_client_fixture: TestClient
):
    def mock_control_ping_failure(*args: object, **kwargs: object) -> list[object]:
        return []

    monkeypatch.setattr("app.core.health.current_app.conf.task_always_eager", True)
    monkeypatch.setattr("app.core.health.current_app.control.ping", mock_control_ping_failure)

    response = test_client_fixture.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert "last_check" in response.json()
