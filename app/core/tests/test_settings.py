from app.core import settings
from pytest import MonkeyPatch


def test_get_settings_reads_values_from_environment(monkeypatch: MonkeyPatch):
    settings.get_settings.cache_clear()
    monkeypatch.setenv("JWT_SECRET_KEY", "from-env")

    loaded = settings.get_settings()

    assert loaded.jwt_secret_key == "from-env"

    settings.get_settings.cache_clear()
