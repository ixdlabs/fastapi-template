from fastapi import FastAPI

from app.config import openapi
from app.config.exceptions import register_exception_handlers
from app.config.logging import setup_logging
from app.config.otel import setup_open_telemetry
from app.config.settings import get_settings
from app.features.users import urls as user_urls

settings = get_settings()
setup_logging(settings.logger_name)

app = FastAPI(
    title="Sample API",
    description="This is a sample API built with FastAPI.",
    version="1.0.0",
    contact={"name": "IXD Labs", "url": "https://ixdlabs.com", "email": "sunera@ixdlabs.com"},
    openapi_url="/api/openapi.json",
    docs_url=None,
    redoc_url=None,
)

setup_open_telemetry(app, settings)

app.include_router(openapi.router)
app.include_router(user_urls.router)

register_exception_handlers(app)
