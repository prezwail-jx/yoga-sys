## 1. Private Training Data Model

- [x] 1.1 Add SQLAlchemy domain models for private availability, private booking, and private lesson record with statuses, ownership fields, timestamps, and traceable business references.
- [x] 1.2 Add Alembic migration for private training tables, foreign keys, active-slot uniqueness/locking constraints, and indexes for coach/date/member queries.
- [x] 1.3 Add Pydantic schemas and domain types for availability creation, weekly generation, booking request, confirmation/rejection, sign-in, and lesson records.
- [x] 1.4 Register new models in metadata exports and verify migrations upgrade from current head.

## 2. Private Training Backend Services

- [x] 2.1 Implement availability service for coach/admin create, update, cancel, list, overlap validation, and day/week slot generation.
- [x] 2.2 Implement member private booking service with member status checks, private card eligibility, group/private time-conflict checks, slot locking, concurrency protection, and idempotency.
- [x] 2.3 Implement confirmation/rejection/pending-cancel service that consumes one private card time on confirmation, releases slots on rejection or pending cancellation, and records audit/writeoff events.
- [x] 2.4 Implement private sign-in and lesson record service with role checks, completed status transition, member timeline integration, and immutable audit trail.
- [x] 2.5 Add FastAPI routers and dependency wiring for private availability, private bookings, private sign-in, and private lesson records.
- [x] 2.6 Update group class scheduling and booking services to reject member and coach overlaps with active private training records.

## 3. Private Training Frontend

- [x] 3.1 Replace mock private training API usage with Nuxt BFF proxy routes backed by real FastAPI endpoints.
- [x] 3.2 Update `useGymApi` and frontend types for private availability, private bookings, booking decisions, and lesson records.
- [x] 3.3 Rebuild `/private-training` as a role-aware page: members browse/book slots, coaches publish slots and handle requests, administrators can inspect/manage all private training records.
- [x] 3.4 Add member message, coach confirmation/rejection, slot state, sign-in, lesson content, consumed hours, and member status UI flows.
- [x] 3.5 Remove the private training Mock marker from navigation only after real data paths are in use.

## 4. Reporting Backend

- [x] 4.1 Add reporting query schemas for date range, coach, course, card product, report category, grouping, and pagination filters.
- [x] 4.2 Implement report summary service using real members, member cards, transactions, group class bookings, private bookings, writeoff events, and lesson records.
- [x] 4.3 Implement trend queries for revenue, bookings, attendance, and private lesson completion.
- [x] 4.4 Implement drill-down detail queries for expiring members, transactions/refunds, course attendance, and private training metrics.
- [x] 4.5 Add Excel export generation from the same filtered detail queries, enforce a 180-day synchronous export limit, and return `.xlsx` downloads from backend endpoints.
- [x] 4.6 Add administrator-only report routers and rejected access audit coverage for member/coach attempts.

## 5. Reporting Frontend

- [x] 5.1 Replace mock report API usage with Nuxt BFF proxy routes backed by real reporting endpoints.
- [x] 5.2 Update frontend report types and `useGymApi` methods for summary, trends, drill-down details, and export.
- [x] 5.3 Rebuild `/reports` with date, coach, course, card product, and report category filters.
- [x] 5.4 Add summary cards, trend display, drill-down detail panels/tables, pagination, and navigation links to related records where available.
- [x] 5.5 Add Excel export action that downloads server-generated files using the active filters.
- [x] 5.6 Remove the reports Mock marker from navigation only after real report data and export work.

## 6. Tests And Verification

- [x] 6.1 Add backend unit tests for private availability overlap, ownership rules, booking concurrency, confirmation/rejection, entitlement consumption, sign-in, and access boundaries.
- [x] 6.2 Add backend unit tests for report summaries, trend filters, drill-down reconciliation, Excel export content, and unauthorized access.
- [x] 6.3 Add frontend unit tests for private training role-specific UI states and report filter/export interactions.
- [x] 6.4 Add or update E2E tests covering member private booking request, coach confirmation, private sign-in, admin report viewing, drill-down, and export trigger.
- [x] 6.5 Run backend tests and frontend lint/test commands required by the project, then document any skipped environment-dependent checks.

## 7. Cleanup And Documentation

- [x] 7.1 Retire or clearly isolate obsolete mock routes/data for private slots, private bookings, and reports so production pages cannot accidentally use them.
- [x] 7.2 Update `features.md` and README status tables to mark private training and reporting as real once implementation and tests pass.
- [x] 7.3 Record implementation notes for the resolved questions: one-time private consumption, admin force operation, pending cancellation, cross-module conflicts, weekly conflict handling, and export date-range limits.
