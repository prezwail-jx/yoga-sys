FROM ghcr.io/astral-sh/uv:0.7.5-python3.12-bookworm-slim AS builder

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

COPY uv.lock pyproject.toml ./

RUN uv sync --frozen --no-install-project --no-dev

COPY . /app

RUN uv sync --frozen --no-dev

FROM python:3.12-slim-bookworm

RUN useradd --create-home appuser

WORKDIR /app

COPY --from=builder /app /app
COPY --from=builder --chown=appuser:appuser /app /app

ENV PATH="/app/.venv/bin:$PATH"

USER appuser

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && python -m app.scripts.seed_users && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
