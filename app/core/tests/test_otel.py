from celery import Celery
from fastapi import FastAPI
from pytest import MonkeyPatch
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.otel import setup_open_telemetry
from app.core.settings import Settings
from unittest.mock import MagicMock


def test_setup_open_telemetry_skips_instrumentation_when_disabled(
    db_engine_fixture: AsyncEngine, monkeypatch: MonkeyPatch
):
    mock_intr = MagicMock()
    monkeypatch.setattr("app.core.otel.AsyncioInstrumentor", mock_intr)

    app = FastAPI()
    setup_open_telemetry(app, db_engine_fixture, Settings(otel_enabled=False))
    mock_intr.assert_not_called()


def test_setup_open_telemetry_instruments_fastapi_dependencies_when_enabled(
    db_engine_fixture: AsyncEngine, monkeypatch: MonkeyPatch
):
    mock_asyncio_intr = MagicMock()
    mock_logging_intr = MagicMock()
    mock_sqlalchemy_intr = MagicMock()
    mock_fastapi_intr = MagicMock()
    mock_celery_intr = MagicMock()

    monkeypatch.setattr("app.core.otel.AsyncioInstrumentor", mock_asyncio_intr)
    monkeypatch.setattr("app.core.otel.LoggingInstrumentor", mock_logging_intr)
    monkeypatch.setattr("app.core.otel.SQLAlchemyInstrumentor", mock_sqlalchemy_intr)
    monkeypatch.setattr("app.core.otel.FastAPIInstrumentor", mock_fastapi_intr)
    monkeypatch.setattr("app.core.otel.CeleryInstrumentor", mock_celery_intr)
    monkeypatch.setattr("app.core.otel.set_logger_provider", MagicMock())
    monkeypatch.setattr("app.core.otel.set_tracer_provider", MagicMock())
    monkeypatch.setattr("app.core.otel.set_meter_provider", MagicMock())

    app = FastAPI()
    setup_open_telemetry(app, db_engine_fixture, Settings(otel_enabled=True))

    mock_asyncio_intr().instrument.assert_called_once()
    mock_logging_intr().instrument.assert_called_once()
    mock_sqlalchemy_intr().instrument.assert_called_once_with(
        engine=db_engine_fixture.sync_engine, enable_commenter=True
    )
    mock_fastapi_intr.instrument_app.assert_called_once_with(app)
    mock_celery_intr().instrument.assert_not_called()


def test_setup_open_telemetry_instruments_celery_dependencies_when_enabled(
    db_engine_fixture: AsyncEngine, monkeypatch: MonkeyPatch
):
    mock_asyncio_intr = MagicMock()
    mock_logging_intr = MagicMock()
    mock_sqlalchemy_intr = MagicMock()
    mock_fastapi_intr = MagicMock()
    mock_celery_intr = MagicMock()

    monkeypatch.setattr("app.core.otel.AsyncioInstrumentor", mock_asyncio_intr)
    monkeypatch.setattr("app.core.otel.LoggingInstrumentor", mock_logging_intr)
    monkeypatch.setattr("app.core.otel.SQLAlchemyInstrumentor", mock_sqlalchemy_intr)
    monkeypatch.setattr("app.core.otel.FastAPIInstrumentor", mock_fastapi_intr)
    monkeypatch.setattr("app.core.otel.CeleryInstrumentor", mock_celery_intr)
    monkeypatch.setattr("app.core.otel.set_logger_provider", MagicMock())
    monkeypatch.setattr("app.core.otel.set_tracer_provider", MagicMock())
    monkeypatch.setattr("app.core.otel.set_meter_provider", MagicMock())

    app = Celery()
    setup_open_telemetry(app, db_engine_fixture, Settings(otel_enabled=True))

    mock_asyncio_intr().instrument.assert_called_once()
    mock_logging_intr().instrument.assert_called_once()
    mock_sqlalchemy_intr().instrument.assert_called_once_with(
        engine=db_engine_fixture.sync_engine, enable_commenter=True
    )
    mock_fastapi_intr.instrument_app.assert_not_called()
    mock_celery_intr().instrument.assert_called_once()
