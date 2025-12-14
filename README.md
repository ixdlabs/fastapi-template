# FastAPI Sample Backend

## Cloning

```bash
git clone https://github.com/ixdlabs/fastapi-template
```

## Environment Setup

Requires Python 3.12+ and [uv](https://github.com/astral-sh/uv). uv manages the environment - no venv activation needed.

### Install Requirements

This project ships a `uv.lock` file for reproducible installs. Sync dependencies:

```bash
uv sync
```

### Environment Variables Configuration

Copy `.env.example` to `.env` (create one if missing) and adjust values as needed.

## Formatting and Linting

This project uses [pre-commit](https://pre-commit.com/) hooks and [mypy](https://mypy-lang.org/).

```bash
# install pre-commit hooks to run format checks on commit
uv run pre-commit install
# run formatting pre-commit hooks manually
uv run pre-commit --all-files
# run type checker
uv run mypy .
```

## Testing

Run the test suite (pytest) and optional coverage report:

```bash
uv run pytest
uv run pytest --cov=app --cov-report=term-missing
```

## Database Setup

SQLite is the default for development and will create `sqlite.db` automatically. No additional setup is required to start the API.

To use PostgreSQL or another database, set `DATABASE_URL` to an async SQLAlchemy URL, e.g.:

```
DATABASE_URL=postgresql+asyncpg://db_user:password@localhost:5432/sample_backend
```

### Alembic Migrations

Run migrations after changing models or switching databases:

```bash
# apply migrations
uv run alembic upgrade head
# create a new migration
uv run alembic revision --autogenerate -m "describe change"
```

## OpenTelemetry Setup

This application uses OpenTelemetry (OTel) to export traces, metrics, and logs via OTLP.
[SigNoz](https://signoz.io/) is the recommended backend, but any OTLP-compatible collector will work.

Reference: https://signoz.io/docs/instrumentation/opentelemetry-fastapi/

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

### Running the Application with OpenTelemetry Enabled

> Do not use autoreload when running with OpenTelemetry instrumentation.

Start the application using:

```bash
uv run uvicorn app.main:app
```

### Installing OpenTelemetry Instrumentations

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

## FastAPI Setup

Apply migrations, then start the server:

```bash
uv run fastapi dev app/main.py
```

Interactive docs (RapiDoc) are available at [http://127.0.0.1:8000/api/docs](http://127.0.0.1:8000/api/docs).

### Packages

- [FastAPI](https://fastapi.tiangolo.com/) for the web framework and dependency injection.
- [SQLAlchemy async](https://docs.sqlalchemy.org/en/20/) with Alembic for migrations.
- [Pydantic](https://docs.pydantic.dev/) for request/response models and settings management.
- [PyJWT](https://pyjwt.readthedocs.io/) for JWT authentication.
- [structlog](https://www.structlog.org/) for structured logging.
- [pytest](https://docs.pytest.org/en/stable/) for unit testing.

## Docker / Deployment

Containerization is not bundled here. To containerize, supply `DATABASE_URL` and other env vars, run `uv run alembic upgrade head`, and start the app with `uv run uvicorn app.main:app`.

## Project Structure

```
- app/main.py             - FastAPI app factory and router registration.
- app/config/             - settings, auth, database, logging, pagination, OpenAPI customization, exception handling.
- app/features/users/     - user domain (models, views, urls, tests).
- app/migrations/         - Alembic environment and migration versions.
- uv.lock,pyproject.toml  - dependency and tool definitions managed by uv.
```

## VS Code

Suggested workspace settings to match this repo’s tooling:

```json
{
  "python.testing.pytestArgs": ["app"],
  "python.testing.unittestEnabled": false,
  "python.testing.pytestEnabled": true
}
```

## Localization

Not applicable. The API responses are English-only; translations are not included.

```

```
