# syntax=docker/dockerfile:1.7

FROM ghcr.io/astral-sh/uv:python3.12-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# System deps required to build wheels for packages such as argon2-cffi
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential pkg-config libffi-dev libssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock README.md ./
COPY app ./app

# Install the application into a local virtualenv using the locked dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --group opentelemetry

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:${PATH}"

WORKDIR /app

# Runtime shared libraries for compiled wheels
RUN apt-get update \
    && apt-get install -y --no-install-recommends libssl3 libffi8 \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r app && useradd -r -g app app

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/app /app/app
COPY --from=builder /app/pyproject.toml /app/uv.lock /app/README.md /app/

EXPOSE 8000
USER app

CMD ["uvicorn", "app.fastapi:app", "--host", "0.0.0.0", "--port", "8000"]
