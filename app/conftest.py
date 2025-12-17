import logging
from pathlib import Path
from unittest.mock import MagicMock
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, async_sessionmaker, AsyncSession

from alembic import command, config

from app.config.background import Background, get_background
from app.config.database import get_db_session
from app.config.logging import setup_logging
from app.config.rate_limit import get_rate_limit_strategy
from limits.aio.storage import MemoryStorage
from limits.aio.strategies import MovingWindowRateLimiter, RateLimiter
from app.config.settings import Settings, get_settings
from app.main import app

logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def setup():
    setup_logging("console")
    logger.info("Preparing to run tests...")
    yield


# Database engine for tests using in-memory SQLite
# Run migrations before tests and delete the database file after tests
# This function has to be non-async since it uses alembic, which creates its own event loop
# ----------------------------------------------------------------------------------------------------------------------


@pytest.fixture(scope="session")
def db_engine_fixture(setup: None):
    setup_logging("console")
    Path("sqlite.test.db").unlink(missing_ok=True)
    engine = create_async_engine("sqlite+aiosqlite:///sqlite.test.db", echo=True)

    alembic_cfg = config.Config()
    alembic_cfg.set_main_option("script_location", "app/migrations")
    alembic_cfg.attributes["connection"] = engine
    command.upgrade(alembic_cfg, "head")
    logger.info("Migrations applied for test database.")

    yield engine
    Path("sqlite.test.db").unlink(missing_ok=True)


# Run all in a transaction and roll it back after each test
# ----------------------------------------------------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="function", autouse=True)
async def db_fixture(db_engine_fixture: AsyncEngine):
    async with db_engine_fixture.connect() as connection:
        transaction = await connection.begin()
        try:
            session_maker = async_sessionmaker(bind=connection)
            async with session_maker() as session:
                yield session
        finally:
            await transaction.rollback()


# Background task runner for tests that does not actually run tasks
# ----------------------------------------------------------------------------------------------------------------------


@pytest.fixture(scope="session")
def background_fixture():
    return MagicMock()


# Application settings for tests (this is created with explicit values to ensure reproducibility)
# ----------------------------------------------------------------------------------------------------------------------


@pytest.fixture(scope="function")
def rate_limit_strategy_fixture():
    backend = MemoryStorage()
    strategy = MovingWindowRateLimiter(backend)
    yield strategy


# Application settings for tests (this is created with explicit values to ensure reproducibility)
# ----------------------------------------------------------------------------------------------------------------------


@pytest.fixture(scope="session")
def settings_fixture():
    # Database URL is set to empty string to avoid accidental connections
    return Settings.model_construct(jwt_secret_key="test", database_url="", celery_task_always_eager=True)


# Dependency overrides for tests
# ----------------------------------------------------------------------------------------------------------------------


@pytest.fixture(scope="function", autouse=True)
def override_dependencies(
    db_fixture: AsyncSession,
    settings_fixture: Settings,
    background_fixture: Background,
    rate_limit_strategy_fixture: RateLimiter,
):
    app.dependency_overrides[get_db_session] = lambda: db_fixture
    app.dependency_overrides[get_settings] = lambda: settings_fixture
    app.dependency_overrides[get_background] = lambda: background_fixture
    app.dependency_overrides[get_rate_limit_strategy] = lambda: rate_limit_strategy_fixture

    yield
    app.dependency_overrides.clear()
