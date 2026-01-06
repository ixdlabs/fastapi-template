import logging.config
from unittest.mock import MagicMock
import pytest

from app.core.logging import setup_logging
from app.core.settings import Settings


@pytest.fixture
def dictconfig_fixture(monkeypatch: pytest.MonkeyPatch):
    spy = MagicMock()
    monkeypatch.setattr(logging.config, "dictConfig", spy)
    return spy


def test_setup_logging_without_otel(settings_fixture: Settings, dictconfig_fixture: MagicMock):
    settings_fixture.otel_enabled = False
    settings_fixture.logger_name = "console"
    settings_fixture.logger_level = "info"
    setup_logging(settings_fixture)

    dictconfig_fixture.assert_called_once()
    config = dictconfig_fixture.call_args.args[0]
    handlers = config["loggers"]["root"]["handlers"]
    assert handlers == ["console"]
    assert config["loggers"]["root"]["level"] == "INFO"


def test_setup_logging_with_otel_enabled(settings_fixture: Settings, dictconfig_fixture: MagicMock):
    settings_fixture.otel_enabled = True
    settings_fixture.logger_name = "console"
    settings_fixture.logger_level = "debug"
    setup_logging(settings_fixture)
    dictconfig_fixture.assert_called_once()
    config = dictconfig_fixture.call_args.args[0]
    handlers = config["loggers"]["root"]["handlers"]

    assert "console" in handlers
    assert "otel" in handlers
    assert config["loggers"]["root"]["level"] == "DEBUG"
