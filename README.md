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

## Delivery Status

- US1: Member and card-product master data
- US2: Transactions and card lifecycle controls
- US3: Member timeline and write-off audit chain

## Notes

This repository is intended for learning, engineering practice, and public project showcase.
