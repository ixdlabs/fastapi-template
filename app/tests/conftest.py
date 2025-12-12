import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, async_sessionmaker

from alembic import command, config
import structlog

from app.config.logging import setup_logging
from app.config.settings import Settings

logger = structlog.get_logger()


# Setup logging for tests
# ----------------------------------------------------------------------------------------------------------------------


@pytest.fixture(scope="session", autouse=True)
def run_setup_logging():
    setup_logging("console")
    yield


# Application settings for tests (this is created with explicit values to ensure reproducibility)
# ----------------------------------------------------------------------------------------------------------------------


@pytest.fixture(scope="session")
def settings_fixture(run_setup_logging):
    return Settings.model_construct(jwt_secret_key="test", database_url="")


# Database engine for tests using in-memory SQLite
# ----------------------------------------------------------------------------------------------------------------------


@pytest.fixture(scope="session")
def db_engine_fixture(run_setup_logging):
    return create_async_engine("sqlite+aiosqlite:///:memory:", echo=True)


@pytest.fixture
async def db_session(db_engine_fixture: AsyncEngine):
    session_maker = async_sessionmaker(db_engine_fixture)
    async with session_maker() as session:
        yield session


# Run migrations before tests and revert after tests
# ----------------------------------------------------------------------------------------------------------------------


@pytest.fixture(scope="session", autouse=True)
def run_migrations(db_engine_fixture: AsyncEngine):
    alembic_cfg = config.Config()
    alembic_cfg.set_main_option("script_location", "app/migrations")
    alembic_cfg.attributes["connection"] = db_engine_fixture
    command.upgrade(alembic_cfg, "head")
    logger.info("Migrations applied for test database.")
    yield

    logger.info("Reverting migrations for test database.")
    command.downgrade(alembic_cfg, "base")
