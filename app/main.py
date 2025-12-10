from fastapi import FastAPI

from app.config import openapi
from app.config.logging import setup_logging
from app.features.users import urls as user_urls


setup_logging()

app = FastAPI(
    title="Sample API",
    description="This is a sample API built with FastAPI.",
    version="1.0.0",
    contact={"name": "IXD Labs", "url": "https://ixdlabs.com", "email": "sunera@ixdlabs.com"},
    openapi_url="/api/openapi.json",
    docs_url=None,
    redoc_url=None,
)


app.include_router(openapi.router)
app.include_router(user_urls.router)
