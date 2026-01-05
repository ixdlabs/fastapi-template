import pytest
from pathlib import Path
from unittest.mock import MagicMock
from fastapi import Request, UploadFile
from sqlalchemy_file import File
from sqlalchemy_file.storage import StorageManager

from app.core.storage import Storage, setup_storage
from app.core.settings import Settings


@pytest.fixture
def mock_request():
    return MagicMock(spec=Request, base_url="http://testserver/")


@pytest.mark.asyncio
async def test_storage_prepare_reads_uploadfile_and_returns_sqlalchemy_file(
    mock_request: MagicMock, settings_fixture: Settings
):
    storage = Storage(request=mock_request, settings=settings_fixture)
    mock_upload = MagicMock(spec=UploadFile)
    mock_upload.filename = "test.jpg"
    mock_upload.content_type = "image/jpeg"

    async def async_read():
        return b"image_content"

    mock_upload.read = async_read
    result = await storage.prepare(mock_upload)

    assert isinstance(result, File)
    assert result.filename == "test.jpg"
    assert result.content_type == "image/jpeg"


def test_cdn_url_returns_none_when_file_is_none(mock_request: MagicMock, settings_fixture: Settings):
    storage = Storage(request=mock_request, settings=settings_fixture)

    assert storage.cdn_url(None) is None


def test_cdn_url_returns_local_url_when_backend_is_local(
    mock_request: MagicMock, settings_fixture: Settings, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings_fixture, "storage_backend", "local")
    storage = Storage(request=mock_request, settings=settings_fixture)
    mock_file = MagicMock()
    mock_file.id = "file-123"
    url = storage.cdn_url(mock_file)

    assert str(url) == "http://testserver/storage/file-123"


def test_cdn_url_returns_remote_url_when_backend_is_dummy(
    mock_request: MagicMock, settings_fixture: Settings, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings_fixture, "storage_backend", "dummy")
    storage = Storage(request=mock_request, settings=settings_fixture)
    mock_file = {"url": "http://cdn.example.com/file-123"}
    url = storage.cdn_url(mock_file)  # pyright: ignore[reportArgumentType, reportCallIssue]

    assert url == "http://cdn.example.com/file-123"


def test_setup_storage_configures_local_backend(
    settings_fixture: Settings, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings_fixture, "storage_backend", "local")
    monkeypatch.setattr(settings_fixture, "storage_local_base_path", str(tmp_path))
    mock_driver_cls = MagicMock()
    mock_driver = mock_driver_cls.return_value
    mock_container = MagicMock()
    mock_driver.get_container.return_value = mock_container
    monkeypatch.setattr(
        "app.core.storage.LocalStorageDriver",
        mock_driver_cls,
    )
    monkeypatch.setattr(
        "app.core.storage.StorageManager.add_storage",
        MagicMock(),
    )
    setup_storage(settings_fixture)
    files_path = tmp_path / "files"

    assert files_path.exists()
    assert files_path.is_dir()
    mock_driver.get_container.assert_called_once_with("files")
    StorageManager.add_storage.assert_called_once_with("default", mock_container)  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue]


def test_setup_storage_configures_dummy_backend(settings_fixture: Settings, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings_fixture, "storage_backend", "dummy")
    mock_driver_cls = MagicMock()
    mock_driver = mock_driver_cls.return_value
    mock_container = MagicMock()
    mock_driver.create_container.return_value = mock_container
    monkeypatch.setattr(
        "app.core.storage.DummyStorageDriver",
        mock_driver_cls,
    )
    monkeypatch.setattr(
        "app.core.storage.StorageManager.add_storage",
        MagicMock(),
    )
    setup_storage(settings_fixture)

    mock_driver_cls.assert_called_once_with("key", "secret")
    mock_driver.create_container.assert_called_once_with("dummy-container")
    StorageManager.add_storage.assert_called_once_with("default", mock_container)  # pyright: ignore[reportAttributeAccessIssue, reportUnknownMemberType]


def test_setup_storage_raises_error_for_invalid_backend(settings_fixture: Settings, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings_fixture, "storage_backend", "invalid_backend")

    with pytest.raises(ValueError, match="Unsupported storage backend"):
        setup_storage(settings_fixture)
