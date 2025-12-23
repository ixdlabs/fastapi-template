# 🚀 FastAPI Template

A robust, production-ready FastAPI backend with structured tooling, OpenTelemetry, Celery, and more.

## 🧬 Cloning the Repository

```bash
git clone https://github.com/ixdlabs/fastapi-template
```

## ⚙️ Environment Setup

Requires Python 3.12+ and [uv](https://github.com/astral-sh/uv). uv manages the environment - no venv activation needed.

### Install Dependencies

This project uses a `uv.lock` file for consistent dependency installation.

```bash
uv sync
```

### Configure Environment Variables

Copy `.env.example` to `.env` (create one if missing) and adjust values as needed.

## 🧹 Code Formatting & Linting

This project uses [pre-commit](https://pre-commit.com/) hooks and [mypy](https://mypy-lang.org/).

```bash
# Install pre-commit hooks
uv run pre-commit install
# Run formatting checks
uv run pre-commit --all-files
# Type checking
uv run mypy .
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
uv run uvicorn app.main:app
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

The instrumentations should be configured inside the `app/config/otel.py`.

Once configured, traces, metrics, and logs are automatically exported via OTLP and data appears in SigNoz (or your chosen backend).

## ⚡ FastAPI Server

Run after applying migrations:

```bash
uv run fastapi dev app/main.py
```

Docs available at: [http://127.0.0.1:8000/api/docs](http://127.0.0.1:8000/api/docs)

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
uv run celery -A app.worker worker
# Beat Scheduler - schedule periodic tasks
uv run celery -A app.worker beat
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
├── main.py                  # App entry point
├── config/                  # Configuration (env, logging, otel, etc.)
├── features/users/          # User domain logic
├── migrations/              # Alembic migrations
uv.lock, pyproject.toml      # Dependency definitions
```

## 🧠 VS Code Config

```json
{
  "python.testing.pytestArgs": ["app"],
  "python.testing.unittestEnabled": false,
  "python.testing.pytestEnabled": true,
  "editor.rulers": [120]
}
```
