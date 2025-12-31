import logging
from pathlib import Path
from fastapi import APIRouter, UploadFile
from fastapi.responses import FileResponse
from pydantic import HttpUrl
from sqlalchemy_file import File

from sqlalchemy_file.storage import StorageManager
from libcloud.storage.drivers.dummy import DummyStorageDriver
from libcloud.storage.drivers.local import LocalStorageDriver
from app.core.exceptions import ServiceException, raises
from app.core.settings import Settings, SettingsDep


logger = logging.getLogger(__name__)

# Storage endpoint to serve files in development mode
# ----------------------------------------------------------------------------------------------------------------------

router = APIRouter()


class StorageDisabledException(ServiceException):
    status_code = 503
    type = "core/storage/disabled"
    detail = "Storage service is disabled."


@raises(StorageDisabledException)
@router.get("/storage/{file_id}", response_class=FileResponse)
async def get_storage_file(file_id: str, settings: SettingsDep) -> Path:
    """
    Get a file from storage by its file ID.
    This endpoint is intended for development use only and serves files from local storage.
    """
    if settings.storage_backend == "local":
        return Path(settings.storage_local_base_path) / "files" / file_id
    raise StorageDisabledException()


# Utility functions for storage operations
# ----------------------------------------------------------------------------------------------------------------------


async def convert_uploaded_file_to_db(upload_file: UploadFile) -> File:
    """Convert a FastAPI UploadFile to a SQLAlchemy File object."""
    content = await upload_file.read()
    return File(content=content, filename=upload_file.filename, content_type=upload_file.content_type)


def downloadable_url(file: File | None) -> HttpUrl | None:
    """Try to get a download URL for a SQLAlchemy File object."""
    if file is None:
        return None
    storage_backend = StorageManager.get_default()
    if storage_backend == "local":
        # using development mode local storage, return a local URL
        return HttpUrl(f"http://localhost:8000/storage/{file['file_id']}")
    return file["url"]


# Storage setup function
# ----------------------------------------------------------------------------------------------------------------------


def setup_storage(settings: Settings):
    """Initialize storage backends based on application settings."""
    if settings.storage_backend == "local":
        logger.info("Creating local storage backend at %s", settings.storage_local_base_path)
        storage_path = Path(settings.storage_local_base_path)
        storage_path.mkdir(parents=True, exist_ok=True)
        container_path = storage_path / "files"
        container_path.mkdir(parents=True, exist_ok=True)

        driver = LocalStorageDriver(storage_path)
        container = driver.get_container(container_path.name)  # pyright: ignore[reportUnknownMemberType]

    elif settings.storage_backend == "dummy":
        logger.info("Using dummy storage backend (no actual storage)")
        driver = DummyStorageDriver("key", "secret")
        container = driver.create_container("dummy-container")  # pyright: ignore[reportUnknownMemberType]

    else:
        raise ValueError(f"Unsupported storage backend: {settings.storage_backend}")

    StorageManager.add_storage(settings.storage_backend, container)
