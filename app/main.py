from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.config import openapi
from app.config.exceptions import custom_http_exception_handler
from app.config.logging import setup_logging
from app.config.settings import get_settings
from app.features.users import urls as user_urls
from starlette.exceptions import HTTPException


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    setup_logging(settings.server_logger_name)
    yield


app = FastAPI(
    title="Sample API",
    description="This is a sample API built with FastAPI.",
    version="1.0.0",
    contact={"name": "IXD Labs", "url": "https://ixdlabs.com", "email": "sunera@ixdlabs.com"},
    openapi_url="/api/openapi.json",
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
)


app.include_router(openapi.router)
app.include_router(user_urls.router)

app.exception_handler(HTTPException)(custom_http_exception_handler)
