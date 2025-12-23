import logging
from pathlib import Path
import pytest
import pytest_asyncio
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, async_sessionmaker, AsyncSession

from alembic import command, config

from app.config.auth import Authenticator, get_authenticator
from app.config.background import Background, get_background
from app.config.cache import get_cache_backend
from app.config.database import get_db_session
from app.config.logging import setup_logging
from app.config.rate_limit import get_rate_limit_strategy
from limits.aio.storage import MemoryStorage
from limits.aio.strategies import MovingWindowRateLimiter, RateLimiter
from app.config.settings import Settings, get_settings
from app.main import app
from aiocache import SimpleMemoryCache, BaseCache

logger = logging.getLogger(__name__)

# Application settings for tests (this is created with explicit values to ensure reproducibility)
# ----------------------------------------------------------------------------------------------------------------------


@pytest.fixture(scope="session")
def settings_fixture():
    # Database URL is set to empty string to avoid accidental connections
    return Settings.model_construct(
        jwt_secret_key="test",
        database_url="",
        celery_task_always_eager=True,
        logger_name="console",
    )


@pytest.fixture(scope="session")
def setup_logging_fixture(settings_fixture: Settings):
    setup_logging(settings_fixture)
    yield


# Database engine for tests using in-memory SQLite
# Run migrations before tests and delete the database file after tests
# This function has to be non-async since it uses alembic, which creates its own event loop
# ----------------------------------------------------------------------------------------------------------------------


@pytest.fixture(scope="session")
def db_engine_fixture(setup_logging_fixture: None):
    Path("sqlite.test.db").unlink(missing_ok=True)
    engine = create_async_engine("sqlite+aiosqlite:///sqlite.test.db", echo=True, poolclass=pool.NullPool)

    alembic_cfg = config.Config()
    alembic_cfg.set_main_option("script_location", "app/migrations")
    alembic_cfg.attributes["connection"] = engine
    command.upgrade(alembic_cfg, "head")
    command.downgrade(alembic_cfg, "base")
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


# Authenticator for tests
# ----------------------------------------------------------------------------------------------------------------------


@pytest.fixture(scope="function")
def authenticator_fixture(settings_fixture: Settings):
    return Authenticator(settings_fixture)


# Background task runner for tests that does not actually run tasks
# ----------------------------------------------------------------------------------------------------------------------


class NoOpBackground(Background):
    called_tasks: list[str] = []

    async def submit(self, fn, *args, **kwargs):
        self.called_tasks.append(fn.__name__)


@pytest.fixture(scope="function")
def background_fixture(settings_fixture: Settings):
    return NoOpBackground(settings_fixture)


# Rate limiting strategy for tests using in-memory storage
# ----------------------------------------------------------------------------------------------------------------------


@pytest.fixture(scope="function")
def rate_limit_strategy_fixture():
    backend = MemoryStorage()
    strategy = MovingWindowRateLimiter(backend)
    yield strategy


# Cache backend for tests using in-memory cache
# ----------------------------------------------------------------------------------------------------------------------


@pytest.fixture(scope="function")
def cache_backend_fixture():
    yield SimpleMemoryCache()


# Dependency overrides for tests
# ----------------------------------------------------------------------------------------------------------------------


@pytest.fixture(scope="function", autouse=True)
def override_dependencies(
    db_fixture: AsyncSession,
    settings_fixture: Settings,
    background_fixture: Background,
    rate_limit_strategy_fixture: RateLimiter,
    cache_backend_fixture: BaseCache,
    authenticator_fixture: Authenticator,
):
    app.dependency_overrides[get_db_session] = lambda: db_fixture
    app.dependency_overrides[get_settings] = lambda: settings_fixture
    app.dependency_overrides[get_background] = lambda: background_fixture
    app.dependency_overrides[get_rate_limit_strategy] = lambda: rate_limit_strategy_fixture
    app.dependency_overrides[get_cache_backend] = lambda: cache_backend_fixture
    app.dependency_overrides[get_authenticator] = lambda: authenticator_fixture

    yield
    app.dependency_overrides.clear()
