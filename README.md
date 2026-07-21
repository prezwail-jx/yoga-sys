# Yoga Studio Management System

A full-stack operations system for small yoga studios and boutique gyms, built with Nuxt 3, FastAPI, and PostgreSQL.

The current release delivers the member and card-product core: authentication, member management, card sales and lifecycle operations, write-off consistency, audit trails, and member timelines. Group scheduling, private coaching, dashboards, and reports are visible in the UI but still use demonstration data.

## Delivery Status

| Module | Status | Notes |
|---|---|---|
| Authentication and RBAC | Implemented | Admin, coach, and member roles; backend permission checks are authoritative |
| Member management | Implemented | CRUD, status changes, search, pagination, and soft deletion |
| Card-product management | Implemented | Duration, session, private, and trial card templates |
| Card transactions | Implemented | Purchase, renewal, reissue, refund, and extension |
| Card lifecycle | Implemented | Activation, expiry, freeze, unfreeze, and reminders |
| Write-off engine | Partially delivered | Reserve, commit, refund, and absence APIs exist; no real booking operations page yet |
| Member timeline and audit | Implemented | Transaction, write-off, and audit replay by member |
| Dashboard | Mock | Project-status placeholder only |
| Group schedule | Mock | Read-only demonstration data |
| Private coaching | Mock | Read-only demonstration data |
| Reports | Mock | Demonstration summary data without export |

See [features.md](./features.md) for the detailed feature inventory and roadmap.

## Architecture

~~~text
Browser
  -> Nuxt 3 frontend and BFF (http://127.0.0.1:3000)
  -> FastAPI backend          (http://127.0.0.1:8000)
  -> PostgreSQL 16
~~~

- Frontend: Vue 3, Nuxt 3, TypeScript, Nuxt UI
- Backend: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic
- Database: PostgreSQL 16
- Reliability: idempotency keys, PostgreSQL transactions, row locks, constraints, and append-only audit events
- Observability: structured logs, request trace IDs, and optional OpenTelemetry OTLP export
- Testing: pytest, Vitest, Playwright, and OpenAPI contract validation

## Project Structure

~~~text
backend/      FastAPI application, migrations, domain services, and tests
frontend/     Nuxt application, BFF routes, components, and tests
docs/         Product requirements
specs/        Specifications, plans, tasks, contracts, and acceptance evidence
features.md   Current feature inventory and roadmap
~~~

## Prerequisites

- Python 3.12
- [uv](https://docs.astral.sh/uv/)
- Node.js 20 LTS and npm
- PostgreSQL 16.x

PostgreSQL is required. Migrations use UUID, JSONB, ENUM, trigram indexes, and the pgcrypto, uuid-ossp, and pg_trgm extensions. SQLite and MySQL are not drop-in replacements.

## Quick Start

### 1. Prepare PostgreSQL

Open PostgreSQL as an administrator:

~~~bash
sudo -u postgres psql
~~~

Create the local role and database, replacing YOUR_LOCAL_PASSWORD:

~~~sql
CREATE ROLE yoga LOGIN PASSWORD 'YOUR_LOCAL_PASSWORD';
CREATE DATABASE yoga_sys OWNER yoga;
~~~

If they already exist, update them instead:

~~~sql
ALTER ROLE yoga WITH LOGIN PASSWORD 'YOUR_LOCAL_PASSWORD';
ALTER DATABASE yoga_sys OWNER TO yoga;
GRANT ALL PRIVILEGES ON DATABASE yoga_sys TO yoga;
~~~

Exit psql and verify connectivity:

~~~bash
PGPASSWORD="YOUR_LOCAL_PASSWORD" psql -h 127.0.0.1 -U yoga -d yoga_sys \
  -c "SELECT current_database(), current_user;"
~~~

Do not create application tables manually. Alembic owns the schema. The yoga role must own the database, or have permission to create extensions, types, tables, constraints, and indexes in the public schema.

### 2. Configure and start the backend

From the repository root:

~~~bash
cd backend
cp .env.example .env
~~~

Review backend/.env and set at least:

~~~env
DATABASE_URL=postgresql+psycopg://yoga:YOUR_LOCAL_PASSWORD@localhost:5432/yoga_sys
JWT_SECRET=replace-with-at-least-32-random-bytes
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
COACH_USERNAME=coach
COACH_PASSWORD=coach123
~~~

The backend and Alembic load backend/.env automatically; source .env is not required.

~~~bash
uv sync
uv run alembic upgrade head
uv run python -m app.scripts.seed_users
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
~~~

Verify the service:

- Health check: <http://127.0.0.1:8000/healthz>
- OpenAPI documentation: <http://127.0.0.1:8000/docs>

~~~bash
curl http://127.0.0.1:8000/healthz
uv run alembic current
~~~

Expected migration head: **0005_perf_indexes (head)**.

### 3. Start the frontend

Keep the backend running and open a second terminal:

~~~bash
cd frontend
npm install
NUXT_BACKEND_BASE_URL=http://127.0.0.1:8000 npm run dev
~~~

Open <http://127.0.0.1:3000/login>.

If unchanged, the local administrator account is **admin / admin123**. These credentials are for local development only. Replace all initial passwords and use a strong JWT secret before deployment.

## What to Try

After signing in as an administrator:

1. Create and search for members in /members.
2. Create duration, session, private, or trial card templates in /cards.
3. Purchase a card and test renewal, reissue, refund, extension, freeze, and unfreeze in /transactions.
4. Open a member business timeline from the member list.
5. Review transaction, write-off, and audit events, including linked write-off chains.

Pages marked **Mock** in the navigation do not persist real scheduling, private-coaching, or report data.

## Testing

### Backend

Integration tests must not use the development database because fixtures migrate and clean their target database.

Create a separate test database once:

~~~bash
sudo -u postgres createdb -O yoga yoga_sys_test
~~~

Run the suite:

~~~bash
cd backend
TEST_DATABASE_URL=postgresql+psycopg://yoga:YOUR_LOCAL_PASSWORD@127.0.0.1:5432/yoga_sys_test \
  uv run pytest
~~~

If TEST_DATABASE_URL is omitted, tests attempt to start PostgreSQL through Testcontainers.

### Frontend

~~~bash
cd frontend
npm test
npm run lint
npm run typecheck
npm run build
~~~

npm test runs both Vitest unit tests and Playwright end-to-end tests.

Latest recorded acceptance result:

- Backend: 36 tests passed, 92% coverage
- Frontend: 6 unit tests and 4 end-to-end tests passed
- ESLint, TypeScript type checking, and production build passed

## Observability

Development mode writes readable structured logs with request duration, status, trace ID, and span ID. Business spans cover transactions, card lifecycle operations, write-offs, and timeline queries.

OpenTelemetry export is optional:

~~~env
LOG_FORMAT=console
OTEL_ENABLED=true
OTEL_SERVICE_NAME=yoga-sys-backend
OTEL_EXPORTER_OTLP_ENDPOINT=
OTEL_TRACES_SAMPLER_ARG=1.0
~~~

Leave OTEL_EXPORTER_OTLP_ENDPOINT empty to run without a collector. To export traces, set it to a compatible OTLP/HTTP traces endpoint, such as http://localhost:4318/v1/traces.

## Documentation

- [Product requirements](./docs/prd.md)
- [Current feature inventory](./features.md)
- [Feature specification](./specs/002-member-card-core/spec.md)
- [Implementation plan](./specs/002-member-card-core/plan.md)
- [Task breakdown](./specs/002-member-card-core/tasks.md)
- [Detailed quick start](./specs/002-member-card-core/quickstart.md)
- [Acceptance report](./specs/002-member-card-core/checklists/acceptance-report.md)
- [OpenAPI contract](./specs/002-member-card-core/contracts/member-card-core.openapi.yaml)

## Development Notes

This project follows a specification-first workflow: PRD -> specification -> plan -> tasks -> implementation -> acceptance evidence.

The current roadmap prioritizes a real group-class scheduling, booking, attendance, and write-off workflow before private coaching, analytics, notifications, and member-facing applications.
