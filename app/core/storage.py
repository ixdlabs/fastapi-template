import logging
from pathlib import Path
from typing import Annotated, overload
from fastapi import Depends, FastAPI, Request, UploadFile
from pydantic import HttpUrl
from sqlalchemy_file import File

from sqlalchemy_file.storage import StorageManager
from libcloud.storage.drivers.dummy import DummyStorageDriver
from libcloud.storage.drivers.local import LocalStorageDriver
from fastapi.staticfiles import StaticFiles
from app.core.settings import Settings, SettingsDep


logger = logging.getLogger(__name__)

# Storage class
# ----------------------------------------------------------------------------------------------------------------------


class Storage:
    def __init__(self, request: Request, settings: Settings):
        super().__init__()
        self.request = request
        self.settings = settings

    async def prepare(self, upload_file: UploadFile) -> File:
        """Convert a FastAPI UploadFile to a SQLAlchemy File object."""
        content = await upload_file.read()
        return File(content=content, filename=upload_file.filename, content_type=upload_file.content_type)

    @overload
    def cdn_url(self, file: None) -> None: ...

    @overload
    def cdn_url(self, file: File) -> HttpUrl: ...

    def cdn_url(self, file: File | None) -> HttpUrl | None:
        """Try to get a download URL for a SQLAlchemy File object."""
        if file is None:
            return None
        if self.settings.storage_backend == "local":
            return HttpUrl(f"{self.request.base_url}storage/{file.id}")
        return file["url"]


def get_storage(request: Request, settings: SettingsDep) -> Storage:
    return Storage(request, settings)


StorageDep = Annotated[Storage, Depends(get_storage)]

# Storage setup function
# ----------------------------------------------------------------------------------------------------------------------


def setup_storage(app: FastAPI, settings: Settings):
    """Initialize storage backends based on application settings."""
    try:
        _ = StorageManager.get_default()
        return  # Storage already set up
    except RuntimeError:
        pass

    if settings.storage_backend == "local":
        logger.info("Creating local storage backend at %s", settings.storage_local_base_path)
        storage_path = Path(settings.storage_local_base_path)
        storage_path.mkdir(parents=True, exist_ok=True)
        container_path = storage_path / "files"
        container_path.mkdir(parents=True, exist_ok=True)

        driver = LocalStorageDriver(storage_path)
        container = driver.get_container(container_path.name)  # pyright: ignore[reportUnknownMemberType]
        app.mount("/storage", StaticFiles(directory=container_path), name="storage")

    elif settings.storage_backend == "dummy":
        logger.info("Using dummy storage backend (no actual storage)")
        driver = DummyStorageDriver("key", "secret")
        container = driver.create_container("dummy-container")  # pyright: ignore[reportUnknownMemberType]

    else:
        raise ValueError(f"Unsupported storage backend: {settings.storage_backend}")

    StorageManager.add_storage(settings.storage_backend, container)
