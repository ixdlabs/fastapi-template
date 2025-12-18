from fastapi import FastAPI
import uvicorn
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.cors import CORSMiddleware

from app.config import openapi
from app.config.database import create_db_engine_from_settings
from app.config.exceptions import register_exception_handlers
from app.config.logging import setup_logging
from app.config.otel import setup_open_telemetry
from app.config.settings import get_settings

from app.features import model_registry  # noqa: F401
from app.features import task_registry  # noqa: F401
from app.features import router_registry
from app.worker import app as celery_app  # noqa: F401

settings = get_settings()
setup_logging(settings)

app = FastAPI(
    title="Sample API",
    description="This is a sample API built with FastAPI.",
    version="1.0.0",
    contact={"name": "IXD Labs", "url": "https://ixdlabs.com", "email": "sunera@ixdlabs.com"},
    openapi_url="/api/openapi.json",
    docs_url=None,
    redoc_url=None,
)

db_engine = create_db_engine_from_settings(settings)
setup_open_telemetry(app, db_engine, settings)

app.include_router(openapi.router)
app.include_router(router_registry.router)

register_exception_handlers(app)

# Enforces that all incoming requests must be https.
# https://fastapi.tiangolo.com/advanced/middleware/#integrated-middlewares
if not settings.debug:
    app.add_middleware(HTTPSRedirectMiddleware)

# Enforces that all incoming requests have a correctly set Host header (to guard against HTTP Host Header attacks).
# https://fastapi.tiangolo.com/advanced/middleware/#trustedhostmiddleware
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)

# Add appropriate CORS headers to outgoing responses in order to allow cross-origin requests from browsers.
# https://www.starlette.dev/middleware/
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Main entry point
# ----------------------------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
