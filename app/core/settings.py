"""
This file contains code to load environment variables from a .env file
and provide application settings using Pydantic's BaseSettings.
The settings are provided as a dependency to enable easy testing.

Pydantic Docs: https://docs.pydantic.dev/latest/concepts/pydantic_settings <br/>
Fast API Docs: https://fastapi.tiangolo.com/advanced/settings
"""

from functools import lru_cache
from typing import Annotated, Literal

from fastapi import Depends
from pydantic_settings import BaseSettings, SettingsConfigDict
from fast_depends import Depends as WorkerDepends

# Application settings class.
# These are loaded from a .env file.
# ----------------------------------------------------------------------------------------------------------------------


class Settings(BaseSettings):
    allowed_hosts: list[str] = ["*"]
    cors_origins: list[str] = ["*"]

    debug: bool = False
    logger_name: str = "console"
    logger_level: str = "info"

    jwt_secret_key: str = "local"
    jwt_access_expiration_minutes: int = 5
    jwt_refresh_expiration_minutes: int = 24 * 60

    email_verification_expiration_minutes: int = 60 * 24
    password_reset_expiration_minutes: int = 60

    database_url: str = "sqlite+aiosqlite:///./sqlite.db"

    cache_url: str = "memory://"

    rate_limit_backend_url: str = "async+memory://"

    celery_task_always_eager: bool = False
    celery_broker_url: str = "sqla+sqlite:///sqlite.celery.db"
    celery_result_backend_url: str = "rpc"
    celery_timezone: str = "UTC"

    otel_enabled: bool = False
    otel_resource_service_name: str = "backend"
    otel_resource_environment: str = "development"
    otel_exporter_otlp_endpoint: str = ""
    otel_exporter_otlp_insecure: bool = False
    otel_exporter_otlp_headers: str = ""

    email_sender_type: Literal["local", "smtp"] = "local"
    email_smtp_host: str = "localhost"
    email_smtp_port: int = 25
    email_smtp_username: str | None = None
    email_smtp_password: str | None = None
    email_smtp_use_tls: bool = False
    email_smtp_use_ssl: bool = False
    email_sender_address: str = "from@example.com"

    storage_backend: Literal["local", "dummy"] = "local"
    storage_local_base_path: str = "./.storage"

    feature_flags: set[str] = set()

    frontend_base_url: str = "http://localhost:3000"

    model_config = SettingsConfigDict(env_file=".env")


# Dependency that provides application settings.
# The settings are cached to avoid recreating them on each request.
# ----------------------------------------------------------------------------------------------------------------------


@lru_cache
def get_settings():
    return Settings()


SettingsDep = Annotated[Settings, Depends(get_settings)]
SettingsWorkerDep = Annotated[Settings, WorkerDepends(get_settings)]
