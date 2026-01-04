# 🚀 FastAPI Template

A robust, production-ready FastAPI backend with structured tooling, OpenTelemetry, Celery, and more.

## 🧬 Cloning the Repository

```bash
git clone https://github.com/ixdlabs/fastapi-template
```

## ⚙️ Environment Setup

Requires Python 3.14+ and [uv](https://github.com/astral-sh/uv). uv manages the environment - no venv activation needed.

### Install Dependencies

This project uses a `uv.lock` file for consistent dependency installation.

```bash
uv sync
```

### Configure Environment Variables

Copy `.env.example` to `.env` (create one if missing) and adjust values as needed.

## 🧹 Code Formatting & Linting

This project uses [pre-commit](https://pre-commit.com/) hooks with [ruff](https://docs.astral.sh/ruff/) and [pyright](https://microsoft.github.io/pyright/#/) strict mode.

```bash
# Install pre-commit hooks
uv run pre-commit install
# Run formatting and type checks
uv run pre-commit --all-files
```

## ✅ Running Tests

Run the test suite (pytest):

```bash
uv run pytest
```

## 🗄️ Database Configuration

SQLite is the default for development and will create `sqlite.db` automatically.
No additional setup is required to start the API.

For development, PostgreSQL is strongly recommended.
Using a different database engine may lead to issues when generating migrations.

To switch to PostgreSQL, set:

```bash
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/dbname
```

### Alembic Migrations

Run migrations after changing models or switching databases:

```bash
# Apply migrations
uv run alembic upgrade head
# Create new migration
uv run alembic revision --autogenerate -m "describe change"
# Downgrade one migration
uv run alembix downgrade -1
```

## 📈 Observability with OpenTelemetry

This application uses OpenTelemetry (OTel) to export traces, metrics, and logs via OTLP.
[SigNoz](https://signoz.io/) is the recommended backend, but any OTLP-compatible collector will work.

### Environment Configuration

Add the following variables to `.env` file:

```bash
# Set false (default) to disable otel
OTEL_ENABLED=true

# Resource settings to uniquely identify the service
OTEL_RESOURCE_SERVICE_NAME=backend
OTEL_RESOURCE_ENVIRONMENT=development

# Only OTEL_EXPORTER_OTLP_ENDPOINT is required for self-hosted SigNoz
OTEL_EXPORTER_OTLP_ENDPOINT="https://ingest.<region>.signoz.cloud:443"
OTEL_EXPORTER_OTLP_INSECURE=false
OTEL_EXPORTER_OTLP_HEADERS="signoz-ingestion-key=<your-ingestion-key>"
```

### Running the Application with OTel Enabled

> Do not use autoreload when running with OpenTelemetry instrumentation.

Start the application using:

```bash
uv run uvicorn app.web_app:app
```

### Installing OTel Instrumentations

To discover recommended instrumentations for the environment, run:

```bash
uv run opentelemetry-bootstrap
```

This command lists optional packages (e.g., FastAPI, SQLAlchemy, HTTP clients) that can be instrumented. Select **only the ones that is used directly in the application**.

Install only the instrumentations that are needed:

```bash
uv add --group=opentelemetry <package>
# Example:
# uv add --group=opentelemetry opentelemetry-instrumentation-fastapi
# uv add --group=opentelemetry opentelemetry-instrumentation-sqlalchemy
```

The instrumentations should be configured inside the `app/core/otel.py`.

Once configured, traces, metrics, and logs are automatically exported via OTLP and data appears in SigNoz (or your chosen backend).

## ⚡ FastAPI Server

Run after applying migrations:

```bash
uv run fastapi dev app/web_app.py
```

Docs available at: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## 🧰 Included Packages

- [FastAPI](https://fastapi.tiangolo.com/) for the web framework and dependency injection.
- [SQLAlchemy async](https://docs.sqlalchemy.org/en/20/) with Alembic for migrations.
- [Pydantic](https://docs.pydantic.dev/) for request/response models and settings management.
- [PyJWT](https://pyjwt.readthedocs.io/) for JWT authentication.
- [Celery](https://docs.celeryq.dev/) for background tasks.
- [pytest](https://docs.pytest.org/en/stable/) for unit testing.

## 🎯 Background Tasks with Celery

Celery is configured for async task execution.

### Local Development (Eager Mode)

Run tasks without a worker:

```bash
CELERY_TASK_ALWAYS_EAGER=true
```

### Without Eager Mode

Default queue backend is SQLite. Run following commands to start the worker and the beat scheduler.

```bash
# Worker - do the actual work
uv run celery -A app.worker_app worker
# Beat Scheduler - schedule periodic tasks
uv run celery -A app.worker_app beat
```

### Using RabbitMQ as Broker

Celery is configured to use a SQLite database by default.
To switch to RabbitMQ, start the RabbitMQ service and set the `CELERY_BROKER_URL` environment variable.

```bash
# Start the rabbitmq service using docker:
# docker run -d --hostname rabbitmq --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management
CELERY_BROKER_URL=amqp://guest:guest@localhost//
```

### Using Redis as Backend

Celery is configured to run in eager mode by default.
To use Redis as the results backend, first turn eager mode off and set the `CELERY_RESULT_BACKEND_URL` environment variable.

```bash
# Start the redis service using docker:
# docker run --name redis -d -p 6379:6379 redis
CELERY_RESULT_BACKEND_URL=redis://localhost:6379/0
# Eager mode must be disabled for redis to take effect.
CELERY_TASK_ALWAYS_EAGER=False
```

## 📦 Cache Setup

Cache is configured to use in-memory storage (`memory://`) by default.
To switch to redis, start the redis service and set the `CACHE_URL` environment variable.

```bash
# Start the redis service using docker:
# docker run --name redis -d -p 6379:6379 redis
CACHE_URL=redis://localhost:6379/0
```

## 🚩 Feature Flags

Feature flags can be managed via environment variables and database preferences.
Environment variable flags take precedence over database preferences.
For example, to enable a feature flag named `new_dashboard`, add it to the environment variable `FEATURE_FLAGS` as:

```bash
FEATURE_FLAGS=new_dashboard,another_flag
```

In the database, feature flags are stored as preferences with keys prefixed by `feature_flag.`
(e.g., `feature_flag.new_dashboard`).
The value should be set to `"true"` or `"false"`.

The clients can indicate supported feature flags via the `X-Feature-Flags` request header,
which should contain a comma-separated list of supported flags.

```
X-Feature-Flags: new_dashboard,another_flag
```

The code can check feature flags as follows:

```python
# Check if a feature flag is enabled
if await preferences.enabled_feature_flag("new_dashboard"):
    ...
# Check if a feature flag is supported by the client
if await preferences.supported_feature_flag("new_dashboard"):
    ...
# Check if a feature flag is enabled and supported by the client
if await preferences.enabled_and_supported_feature_flag("new_dashboard"):
    ...
```

## 🐳 Docker Setup

Build & run the production image:

```bash
docker build -t fastapi-template .
docker run --rm -p 8000:8000 --env-file .env fastapi-template
```

For persistent storage, use a volume or PostgreSQL via `DATABASE_URL`.

You can apply migrations in the container before first run if you use an external DB:

```bash
docker run --rm --env-file .env fastapi-template uv run alembic upgrade head
```

## 🧾 Project Structure

```
app/
├─ core/                            # Global configuration & shared infrastructure
│  ├─ emails/                       # Email templates & base components
│  ├─ tests/                        # Core-level tests
│  └─ <module_1>.py
│
├─ features/                        # Feature-based modules (vertical slices)
│  ├─ <domain_1>/                   # Example feature/domain
│  │  ├─ models/                    # Database models
│  │  │  ├─ tests/                  # Model tests
│  │  │  └─ <model_1>.py
│  │  │
│  │  ├─ services/                  # Business logic & API handlers
│  │  │  ├─ common/                 # Endpoints shared across user types
│  │  │  ├─ <user_type>/            # User-type–specific endpoints
│  │  │  └─ tasks/                  # Async/worker services
│  │  │     ├─ tests/               # Task tests
│  │  │     └─ <do_action>.py       # **Single-responsibility task
│  │  │
│  │  ├─ api.py                     # Feature-level API router
│  │  └─ tasks.py                   # Feature-level Celery task registry
│  │
│  ├─ api.py                        # Aggregate feature routers
│  ├─ tasks.py                      # Aggregate feature tasks
│  └─ models.py                     # Aggregate feature models
│
├─ fixtures/                        # Test factories & fixtures
│  └─ <model_1_factory>.py
│
├─ migrations/                      # Alembic migration root
│  ├─ versions/                     # Migration files
│  │  └─ <datetime>_<id>_<slug>.py
│  ├─ env.py                        # Alembic runtime configuration
│  └─ script.mako                   # Migration template
│
├─ conftest.py                      # Pytest global configuration
├─ fastapi.py                       # FastAPI app factory / wiring
├─ web_app.py                       # Web application entry point
├─ celery.py                        # Celery app factory / wiring
├─ worker_app.py                    # Worker entry point
│
├─ pyproject.toml                   # Project metadata & dependencies
└─ uv.lock                          # Dependency lockfile
```

The single responsibility task should have below structure.

```python
# ... imports

logger = logging.getLogger(__name__)

router = APIRouter()          # ... for API endpoints
registry = TaskRegistry()     # ... for worker tasks


# Input/Output
# -----------------------------------------------------------------------------


class DoActionInput(BaseModel):
  ...


class DoActionOutput(BaseModel):
  ...


# Exceptions
# -----------------------------------------------------------------------------


class Example1Exception(ServiceException):
    status_code = status.HTTP_404_NOT_FOUND
    type = "<domain>/<user-type>/<do-action>/example-exception-1"
    detail = "Example exception 1 message"


# Action
# -----------------------------------------------------------------------------


# ... for API endpoints
@raises(Example1Exception)
@router.post("/do-action")
async def do_action(form: DoActionInput, dep1: Example1Dep, ...) -> DoActionOutput:
    """
    Documentation for the action with any special notes.
    """


# ... for worker tasks
@registry.background_task("do_action")
async def do_action(task_input: DoActionInput, dep1: Example1WorkerDep, ...) -> DoActionOutput:
    """
    Documentation for the action with any special notes.
    """


DoActionTaskDep = Annotated[BackgroundTask, Depends(do_action)]

# ... for service methods
async def do_action(form: DoActionInput, dep1: Example1Dep, ...) -> DoActionOutput:
    """
    Documentation for the action with any special notes.
    """

```

The single responsibility task denoting a worker task should have below structure.

## 🧠 VS Code Config

```json
{
  "python.testing.pytestArgs": ["app"],
  "python.testing.unittestEnabled": false,
  "python.testing.pytestEnabled": true,
  "editor.rulers": [120]
}
```
