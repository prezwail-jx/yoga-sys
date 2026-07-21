## 1. Data Model And Contracts

- [x] 1.1 Add Alembic migration for courses, rooms, coach profiles, class sessions, bookings, account bindings, constraints and indexes
- [x] 1.2 Implement SQLAlchemy domain models and register metadata exports
- [x] 1.3 Implement Pydantic schemas for catalog, scheduling, booking and member account APIs
- [x] 1.4 Extend the OpenAPI contract and contract tests for all new secured and idempotent endpoints

## 2. Catalog And Scheduling Backend

- [x] 2.1 Implement repositories and services for course, room and coach profile management
- [x] 2.2 Implement admin catalog CRUD endpoints with role enforcement and validation
- [x] 2.3 Implement class session repository and scheduling service with resource conflict checks
- [x] 2.4 Implement weekly schedule query, lifecycle actions and copy-week behavior

## 3. Member Account Binding

- [x] 3.1 Extend authentication to create bound member and coach accounts and issue resource-scoped JWTs
- [x] 3.2 Add admin member/coach account endpoints and enforce unique active resource binding
- [x] 3.3 Add authentication and cross-member isolation tests

## 4. Booking And Write-Off Backend

- [x] 4.1 Implement booking repository with row locks, capacity counts and overlap queries
- [x] 4.2 Implement atomic admin proxy booking and member self-booking using reserve_hold
- [x] 4.3 Implement deadline-aware cancellation and check-in with terminal write-off events
- [x] 4.4 Implement class cancellation and admin completion with batch absence processing
- [x] 4.5 Add audit, timeline summaries, idempotency and observability spans for booking actions

## 5. Frontend

- [x] 5.1 Add domain types, API composables and Nuxt BFF routes for catalog, sessions, bookings and account creation
- [x] 5.2 Build catalog management and replace the Mock schedule page with a responsive weekly schedule and session editor
- [x] 5.3 Build the class session operations page for proxy booking, cancellation, check-in and completion
- [x] 5.4 Build member schedule and my-bookings views with self-service booking and cancellation
- [x] 5.5 Add member and coach account creation actions and role-aware navigation and route guards

## 6. Verification And Documentation

- [x] 6.1 Add unit and integration tests for scheduling rules and booking state transitions
- [x] 6.2 Add concurrency tests for the final seat, duplicate booking and terminal-event exclusion
- [x] 6.3 Add frontend unit and end-to-end coverage for admin and member flows
- [x] 6.4 Add performance and capacity test entry points for write p95, timeline p95 and target data volume
- [x] 6.5 Update features.md, quickstart and acceptance traceability with actual implementation status
- [x] 6.6 Run backend and frontend test, lint and build suites and record results
- [x] 6.7 Validate specific-course card product IDs on create and update, add regression coverage, and rerun verification suites
