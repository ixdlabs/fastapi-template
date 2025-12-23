import datetime
import zoneinfo
import time_machine
import tzlocal
from app.config import settings
from pytest import MonkeyPatch


def test_get_settings_respects_environment(monkeypatch: MonkeyPatch):
    settings.get_settings.cache_clear()
    monkeypatch.setenv("JWT_SECRET_KEY", "from-env")

    loaded = settings.get_settings()

    assert loaded.jwt_secret_key == "from-env"

    settings.get_settings.cache_clear()


def test_settings_timezone_is_respected():
    loaded = settings.get_settings()

    local_tz = tzlocal.get_localzone()
    assert loaded.server_timezone == "UTC"
    assert str(local_tz) == "UTC"

    with time_machine.travel("2024-01-01 12:00:00"):
        now_utc = datetime.datetime.now(datetime.timezone.utc)
    with time_machine.travel("2024-01-01 12:00:00"):
        now_no_tz = datetime.datetime.now()
    with time_machine.travel("2024-01-01 12:00:00"):
        now_different_tz = datetime.datetime.now(tz=zoneinfo.ZoneInfo("America/New_York"))

    assert now_utc.replace(tzinfo=None) == now_no_tz
    assert now_different_tz.replace(tzinfo=None) != now_no_tz
