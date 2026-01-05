import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.testclient import TestClient
from app.fixtures.preference_factory import PreferenceFactory

URL = "/api/v1/common/preferences"


# ----------------------------------------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_anyone_can_list_global_preferences(test_client_fixture: TestClient, db_fixture: AsyncSession):
    preferences = [
        PreferenceFactory.build(key="pref1", value="value1", is_global=True),
        PreferenceFactory.build(key="pref2", value="value2", is_global=False),
        PreferenceFactory.build(key="pref3", value="value3", is_global=True),
        PreferenceFactory.build(key="pref4", value="value4", is_global=False),
    ]
    db_fixture.add_all(preferences)
    await db_fixture.commit()

    response = test_client_fixture.get(URL)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["key"] == "pref1"
    assert data[0]["value"] == "value1"
    assert data[1]["key"] == "pref3"
    assert data[1]["value"] == "value3"
