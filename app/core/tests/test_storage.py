import pytest
from pathlib import Path
from unittest.mock import MagicMock
from fastapi import FastAPI, Request, UploadFile
from sqlalchemy_file import File

from app.core.storage import Storage, setup_storage
from app.core.settings import Settings


@pytest.fixture
def mock_request():
    request = MagicMock(spec=Request, base_url="http://testserver/")
    return request


@pytest.mark.asyncio
async def test_storage_prepare_reads_and_uploadfile_and_converts_to_sqlalchemy_file(
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
    # Passing a dict to simulate file["url"] behavior since mocking __getitem__ is unnecessarily complicated
    mock_file = {"url": "http://cdn.example.com/file-123"}

    url = storage.cdn_url(mock_file)  # pyright: ignore[reportArgumentType, reportCallIssue]
    assert url == "http://cdn.example.com/file-123"


def test_setup_storage_returns_early_if_already_configured(settings_fixture: Settings, monkeypatch: pytest.MonkeyPatch):
    app = FastAPI()
    mock_manager = MagicMock()
    mock_manager.get_default.return_value = "existing_storage"
    monkeypatch.setattr("sqlalchemy_file.storage.StorageManager", mock_manager)
    setup_storage(app, settings_fixture)

    mock_manager.add_storage.assert_not_called()


def test_setup_storage_configures_local_backend(
    settings_fixture: Settings, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    app = FastAPI()
    app.mount = MagicMock()
    monkeypatch.setattr(settings_fixture, "storage_backend", "local")
    monkeypatch.setattr(settings_fixture, "storage_local_base_path", str(tmp_path / "local_storage"))
    mock_manager = MagicMock()
    mock_driver_cls = MagicMock()
    mock_static_files = MagicMock()
    mock_manager.get_default.side_effect = RuntimeError("Not configured")
    mock_driver_instance = mock_driver_cls.return_value
    mock_container = MagicMock()
    mock_driver_instance.get_container.return_value = mock_container
    monkeypatch.setattr("sqlalchemy_file.storage.StorageManager", mock_manager)
    monkeypatch.setattr("libcloud.storage.drivers.local.LocalStorageDriver", mock_driver_cls)
    monkeypatch.setattr("fastapi.staticfiles.StaticFiles", mock_static_files)
    setup_storage(app, settings_fixture)
    files_path = tmp_path / "local_storage" / "files"

    assert files_path.exists()
    assert files_path.is_dir()
    mock_driver_cls.assert_called_once()
    mock_driver_instance.get_container.assert_called_with("files")
    app.mount.assert_called_once()
    args, kwargs = app.mount.call_args
    assert args[0] == "/storage"
    assert kwargs["name"] == "storage"
    mock_manager.add_storage.assert_called_with("local", mock_container)


def test_setup_storage_configures_dummy_backend(settings_fixture: Settings, monkeypatch: pytest.MonkeyPatch):
    app = FastAPI()
    monkeypatch.setattr(settings_fixture, "storage_backend", "dummy")
    mock_manager = MagicMock()
    mock_driver_cls = MagicMock()
    mock_manager.get_default.side_effect = RuntimeError("Not configured")
    mock_container = MagicMock()
    mock_driver_cls.return_value.create_container.return_value = mock_container
    monkeypatch.setattr("app.core.storage.StorageManager", mock_manager)
    monkeypatch.setattr("app.core.storage.DummyStorageDriver", mock_driver_cls)
    setup_storage(app, settings_fixture)

    mock_driver_cls.assert_called_with("key", "secret")
    mock_manager.add_storage.assert_called_with("dummy", mock_container)


def test_setup_storage_raises_error_for_invalid_backend(settings_fixture: Settings, monkeypatch: pytest.MonkeyPatch):
    app = FastAPI()
    monkeypatch.setattr(settings_fixture, "storage_backend", "invalid_backend")
    mock_manager = MagicMock()
    mock_manager.get_default.side_effect = RuntimeError("Not configured")
    monkeypatch.setattr("app.core.storage.StorageManager", mock_manager)

    with pytest.raises(ValueError, match="Unsupported storage backend: invalid_backend"):
        setup_storage(app, settings_fixture)
