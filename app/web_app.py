import uvicorn

from app.celery import create_celery_app
from app.fastapi import create_fastapi_app
from app.core.logging import setup_logging
from app.core.settings import get_settings
from app.core.storage import setup_storage

global_settings = get_settings()
setup_logging(global_settings)
setup_storage(global_settings)
app = create_fastapi_app(global_settings)

_ = create_celery_app(global_settings)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
