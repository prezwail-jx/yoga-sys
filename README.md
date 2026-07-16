# Yoga Studio Management System

A full-stack management system for small yoga studios and boutique gyms.

Built with a **vibe coding** workflow using **OpenCode** + **Spec-Kit** (spec -> plan -> tasks -> implementation), this project turns a real PRD into an engineering-ready product.

## Overview

This system helps studios manage daily operations in one place:

- Member profiles, status, and history
- Card products and member card lifecycle
- Group class schedule, booking, and check-in/write-off
- Private coaching availability and appointment flow
- Role-based access, audit logs, and analytics dashboards

## Core Capabilities

### Member & Card Management
- Member CRUD with status control (`normal`, `paused`, `expired`, `disabled`)
- Multiple active cards per member
- Card templates: duration cards, session cards, private cards, trial cards
- Lifecycle actions: purchase, renewal, refund, freeze, unfreeze, extension

### Group Classes
- Weekly visual timetable editing and publishing
- Capacity limit and waitlist behavior
- Booking rules (time-window and same-slot constraints)
- QR/manual/admin-assisted check-in flows

### Private Coaching
- Coach profile and specialization data
- Coach-side availability publishing (daily/weekly)
- Member booking and coach confirm/reject workflow
- Session records and notes

### Security, Consistency, and Traceability
- Server-side RBAC as the source of truth (`Admin / Coach / Member`)
- Idempotency protection for critical write operations
- Transaction-safe logic with PostgreSQL constraints and row locks
- Append-only audit events for full timeline replay

## Tech Stack

- Frontend: Nuxt 3, Vue 3, TypeScript, Nuxt UI
- Backend: FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic
- Database: PostgreSQL 16
- Process: OpenAPI-first + acceptance-driven iterative delivery

## Project Structure

```text
backend/      # FastAPI services, domain logic, persistence, tests
frontend/     # Nuxt application (admin and role-facing pages)
docs/         # PRD and product docs
specs/        # Spec-Kit artifacts (spec/plan/tasks/contracts/checklists)
```

## Quick Start

### Prerequisites

- Python 3.12 and [uv](https://docs.astral.sh/uv/)
- Node.js 20 LTS and npm
- PostgreSQL 16.x (PostgreSQL 16.11 is recommended)

This project requires PostgreSQL. The migrations use PostgreSQL-specific UUID,
JSONB and ENUM types, together with the `pgcrypto` and `uuid-ossp` extensions,
so MySQL and SQLite cannot be used as drop-in replacements.

Initialize PostgreSQL by following
[Local Database Initialization](#local-database-initialization-postgresql)
before starting the application.

### Start the backend

Open the first terminal from the repository root:

```bash
cd backend
uv venv
source .venv/bin/activate
uv sync

# Create the local environment file once, then review DATABASE_URL and secrets.
test -f .env || cp .env.example .env

# Load environment variables and initialize the database.
set -a
source .env
set +a
alembic upgrade head
python -m app.scripts.seed_users

# Start FastAPI.
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Verify the backend after it starts:

- Health check: <http://127.0.0.1:8000/healthz>
- API documentation: <http://127.0.0.1:8000/docs>

### Start the frontend

Keep the backend running and open a second terminal from the repository root:

```bash
cd frontend
npm install
npm run dev
```

Open <http://127.0.0.1:3000> and log in with the default local administrator
account: `admin` / `admin123`.

To run backend tests separately:

```bash
cd backend
uv run pytest
```

## Local Database Initialization (PostgreSQL)

### SQL requirements

- PostgreSQL 16.x, listening on `localhost:5432` by default.
- A UTF-8 database named `yoga_sys`.
- A login role named `yoga`; its password must match `DATABASE_URL` in
  `backend/.env`.
- The `yoga` role must own the database, or have permission to create extensions,
  ENUM types, tables and indexes in the `public` schema.
- The PostgreSQL installation must provide the `pgcrypto` and `uuid-ossp`
  extensions. Alembic enables them automatically during the first migration.

Do not create application tables manually. Alembic owns the schema and creates
all required tables, types, constraints and indexes.

### Initialize the local database

1) Enter PostgreSQL as an admin user:

```bash
sudo -u postgres psql
```

2) Create (or update) the application role and database in `psql`. Replace
`YOUR_STRONG_PASSWORD` with a local password and reuse the same value in
`backend/.env`:

```sql
DO $$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'yoga') THEN
      CREATE ROLE yoga LOGIN PASSWORD 'YOUR_STRONG_PASSWORD';
   ELSE
      ALTER ROLE yoga WITH LOGIN PASSWORD 'YOUR_STRONG_PASSWORD';
   END IF;
END$$;

SELECT 'CREATE DATABASE yoga_sys OWNER yoga'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'yoga_sys')\gexec

GRANT ALL PRIVILEGES ON DATABASE yoga_sys TO yoga;
```

3) Verify connectivity:

```bash
PGPASSWORD="YOUR_STRONG_PASSWORD" psql -h localhost -U yoga -d yoga_sys -c "SELECT current_database(), current_user;"
```

4) From the repository root, create the backend environment file if it does not
already exist:

```bash
test -f backend/.env || cp backend/.env.example backend/.env
```

Set `DATABASE_URL` in `backend/.env` to:

```bash
DATABASE_URL=postgresql+psycopg://yoga:YOUR_STRONG_PASSWORD@localhost:5432/yoga_sys
```

5) Run all database migrations with the environment loaded:

```bash
cd backend
set -a
source .env
set +a
uv run alembic upgrade head
```

6) Verify required tables:

```bash
PGPASSWORD="YOUR_STRONG_PASSWORD" psql -h localhost -U yoga -d yoga_sys -c "SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name;"
```

Expected tables include `admin_user`, `audit_log`, `card_product`,
`idempotency_record` and `member`. If migration reports a permission error,
confirm that `yoga` owns `yoga_sys` and has `CREATE` permission on the `public`
schema.

## Delivery Status

- US1: Member and card-product master data
- US2: Transactions and card lifecycle controls
- US3: Member timeline and write-off audit chain

## Notes

This repository is intended for learning, engineering practice, and public project showcase.
