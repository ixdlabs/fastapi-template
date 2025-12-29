import logging
from pathlib import Path
from fastapi import FastAPI
import pytest
from fastapi.testclient import TestClient
import pytest_asyncio
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, async_sessionmaker, AsyncSession

from alembic import command, config

from app.core.auth import AuthUser, Authenticator, get_authenticator, get_current_user
from app.core.cache import get_cache_backend
from app.core.database import get_db_session
from app.core.logging import setup_logging
from app.core.rate_limit import get_rate_limit_strategy
from app.fixtures.user_factory import UserFactory
from limits.aio.storage import MemoryStorage
from limits.aio.strategies import MovingWindowRateLimiter, RateLimiter
from app.core.settings import Settings, get_settings
from app.features.users.models.user import UserType, User
from aiocache import SimpleMemoryCache, BaseCache

from app.main import create_fastapi_app
from app.worker import create_celery_app

logger = logging.getLogger(__name__)

# Application settings for tests (this is created with explicit values to ensure reproducibility)
# ----------------------------------------------------------------------------------------------------------------------


@pytest.fixture(scope="session")
def settings_fixture():
    return Settings.model_construct(
        jwt_secret_key="test",
        database_url="sqlite+aiosqlite:///sqlite.test.db",
        celery_task_always_eager=True,
        celery_broker_url="sqla+sqlite:///sqlite.celery.db",
        celery_result_backend_url="rpc",
        logger_name="console",
        email_sender_type="local",
        email_verification_expiration_minutes=30,
        password_reset_expiration_minutes=45,
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


# Celery fixtures
# ----------------------------------------------------------------------------------------------------------------------


@pytest.fixture(scope="session")
def celery_config(settings_fixture: Settings):
    return {
        "broker_url": settings_fixture.celery_broker_url,
        "result_backend": settings_fixture.celery_result_backend_url,
    }


@pytest.fixture(scope="session")
def use_celery_app_trap():
    return True


@pytest.fixture(scope="session")
def celery_enable_logging():
    return True


@pytest.fixture(scope="function", autouse=True)
def celery_app_fixture(settings_fixture: Settings):
    yield create_celery_app(settings_fixture)


# Authenticator for tests
# ----------------------------------------------------------------------------------------------------------------------


@pytest.fixture(scope="function")
def authenticator_fixture(settings_fixture: Settings):
    return Authenticator(settings_fixture)


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
def fastapi_app_fixture(
    db_fixture: AsyncSession,
    settings_fixture: Settings,
    rate_limit_strategy_fixture: RateLimiter,
    cache_backend_fixture: BaseCache,
    authenticator_fixture: Authenticator,
):
    app = create_fastapi_app(settings_fixture)
    app.dependency_overrides[get_db_session] = lambda: db_fixture
    app.dependency_overrides[get_settings] = lambda: settings_fixture
    app.dependency_overrides[get_rate_limit_strategy] = lambda: rate_limit_strategy_fixture
    app.dependency_overrides[get_cache_backend] = lambda: cache_backend_fixture
    app.dependency_overrides[get_authenticator] = lambda: authenticator_fixture
    yield app


@pytest.fixture(scope="function")
def test_client_fixture(fastapi_app_fixture: FastAPI):
    client = TestClient(fastapi_app_fixture)
    yield client


# Fake user log in for tests
# ----------------------------------------------------------------------------------------------------------------------


async def get_auth_user(type: UserType, db_fixture: AsyncSession) -> tuple[User, AuthUser]:
    user: User = UserFactory.build(type=type)
    db_fixture.add(user)
    await db_fixture.commit()
    await db_fixture.refresh(user)
    return user, AuthUser(
        id=user.id,
        type=user.type.value,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
    )


@pytest_asyncio.fixture(scope="function")
async def authenticated_user_fixture(fastapi_app_fixture: FastAPI, db_fixture: AsyncSession):
    user, auth_user = await get_auth_user(UserType.CUSTOMER, db_fixture)
    fastapi_app_fixture.dependency_overrides[get_current_user] = lambda: auth_user
    yield user


@pytest_asyncio.fixture(scope="function")
async def authenticated_admin_fixture(fastapi_app_fixture: FastAPI, db_fixture: AsyncSession):
    user, auth_user = await get_auth_user(UserType.ADMIN, db_fixture)
    fastapi_app_fixture.dependency_overrides[get_current_user] = lambda: auth_user
    yield user
