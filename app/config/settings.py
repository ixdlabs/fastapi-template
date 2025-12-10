# This file contains code to load environment variables from a .env file
# and provide application settings using Pydantic's BaseSettings.
# The settings are provided as a dependency to enable easy testing.
# Pydantic Docs: https://docs.pydantic.dev/latest/concepts/pydantic_settings
# Fast API Docs: https://fastapi.tiangolo.com/advanced/settings

from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    theme_color_primary: str = "#61A60A"
    theme_color_background: str = "#111827"

    database_url: str = "sqlite+aiosqlite:///./sqlite.db"

    model_config = SettingsConfigDict(env_file=".env")


@lru_cache
def get_settings():
    return Settings()


SettingsDep = Annotated[Settings, Depends(get_settings)]
