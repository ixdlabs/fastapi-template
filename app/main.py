from fastapi import FastAPI

from app.config import openapi
from app.config.logging import setup_logging

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


@app.get("/")
async def root():
    return {"message": "Hello World"}
