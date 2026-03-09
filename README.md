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

```bash
# Backend
cd backend
uv venv
source .venv/bin/activate
uv sync
pytest

# Frontend
cd frontend
npm install
npm run dev
```

## Local Database Initialization (PostgreSQL)

Use this section to prepare a local PostgreSQL database for backend development.

1) Enter PostgreSQL as an admin user:

```bash
sudo -u postgres psql
```

2) Create (or update) app role and database in psql:

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

4) Create backend environment file:

```bash
cp backend/.env.example backend/.env
```

Set `DATABASE_URL` in `backend/.env` to:

```bash
DATABASE_URL=postgresql+psycopg://yoga:YOUR_STRONG_PASSWORD@localhost:5432/yoga_sys
```

5) Run database migrations:

```bash
cd backend
uv run alembic upgrade head
```

6) Verify required tables:

```bash
PGPASSWORD="YOUR_STRONG_PASSWORD" psql -h localhost -U yoga -d yoga_sys -c "SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name;"
```

Expected foundation tables include `audit_log` and `idempotency_record`.

## Delivery Status

- US1: Member and card-product master data
- US2: Transactions and card lifecycle controls
- US3: Member timeline and write-off audit chain

## Notes

This repository is intended for learning, engineering practice, and public project showcase.
