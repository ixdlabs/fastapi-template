"""
This file contains code to load environment variables from a .env file
and provide application settings using Pydantic's BaseSettings.
The settings are provided as a dependency to enable easy testing.

Pydantic Docs: https://docs.pydantic.dev/latest/concepts/pydantic_settings <br/>
Fast API Docs: https://fastapi.tiangolo.com/advanced/settings
"""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from pydantic_settings import BaseSettings, SettingsConfigDict

# Application settings class.
# These are loaded from a .env file.
# ----------------------------------------------------------------------------------------------------------------------


class Settings(BaseSettings):
    allowed_hosts: list[str] = ["*"]
    cors_origins: list[str] = ["*"]

    theme_color_primary: str = "#61A60A"
    theme_color_background: str = "#111827"

    debug: bool = False
    logger_name: str = "console"
    logger_level: str = "info"

    jwt_secret_key: str = "local"
    jwt_expiration_minutes: int = 24 * 60

    database_url: str = "sqlite+aiosqlite:///./sqlite.db"

    celery_task_always_eager: bool = False
    celery_broker_url: str = "sqla+sqlite:///sqlite.celery.db"
    celery_timezone: str = "UTC"

    otel_enabled: bool = False
    otel_resource_service_name: str = "backend"
    otel_resource_environment: str = "development"
    otel_exporter_otlp_endpoint: str = ""
    otel_exporter_otlp_insecure: bool = False
    otel_exporter_otlp_headers: str = ""

    model_config = SettingsConfigDict(env_file=".env")


# Dependency that provides application settings.
# The settings are cached to avoid recreating them on each request.
# ----------------------------------------------------------------------------------------------------------------------


@lru_cache
def get_settings():
    return Settings()


SettingsDep = Annotated[Settings, Depends(get_settings)]
