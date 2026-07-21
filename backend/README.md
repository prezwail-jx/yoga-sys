# Yoga Sys Backend

FastAPI service for authentication, members, card products, card transactions, lifecycle operations, write-offs, audit logs, and member timelines.

For PostgreSQL setup and frontend instructions, see the [project README](../README.md).

## Start the Service

~~~bash
cp .env.example .env
# Review DATABASE_URL, JWT_SECRET, and local account passwords.

uv sync
uv run alembic upgrade head
uv run python -m app.scripts.seed_users
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
~~~

The service and Alembic automatically load backend/.env.

- Health check: <http://127.0.0.1:8000/healthz>
- OpenAPI documentation: <http://127.0.0.1:8000/docs>

## Run Tests

Use an isolated database; do not point the test suite at yoga_sys.

~~~bash
TEST_DATABASE_URL=postgresql+psycopg://yoga:YOUR_LOCAL_PASSWORD@127.0.0.1:5432/yoga_sys_test \
  uv run pytest
~~~

Without TEST_DATABASE_URL, pytest attempts to use Testcontainers.
