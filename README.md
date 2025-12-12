# FastAPI Sample Backend

## Cloning

```bash
uv run git clone https://github.com/ixdlabs/sample-backend
```

## Environment Setup

Requires Python 3.12+ and [uv](https://github.com/astral-sh/uv). uv manages the environment - no venv activation needed.

### Install Requirements

This project ships a `uv.lock` file for reproducible installs. Sync dependencies:

```bash
uv run uv sync
```

Confirm the app starts with:

```bash
uv run fastapi dev app/main.py
# or
uv run uvicorn app.main:app --reload
```

### Environment Variables Configuration

Copy `.env.example` to `.env` (create one if missing) and adjust values as needed.

## Formatting and Linting

This project uses [pre-commit](https://pre-commit.com/) hooks and [mypy](https://mypy-lang.org/).

```bash
uv run pre-commit install
uv run pre-commit --all-files
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
uv run alembic upgrade head     # apply migrations
uv run alembic revision --autogenerate -m "describe change"  # create a new migration
```

## FastAPI Setup

Apply migrations, then start the server:

```bash
uv run fastapi dev app/main.py
```

Interactive docs (RapiDoc) are available at [http://127.0.0.1:8000/api/docs](http://127.0.0.1:8000/api/docs).

### Packages

- [FastAPI](https://fastapi.tiangolo.com/) for the web framework and dependency injection.
- [SQLAlchemy 2.x async](https://docs.sqlalchemy.org/en/20/) with Alembic for migrations.
- [Pydantic v2](https://docs.pydantic.dev/) for request/response models and settings management.
- [PyJWT](https://pyjwt.readthedocs.io/) + Argon2 for JWT auth and password hashing.
- [structlog](https://www.structlog.org/) for structured logging.

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
