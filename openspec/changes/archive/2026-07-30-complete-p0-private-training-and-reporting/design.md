## Context

The system already has real member, card product, member card, transaction, group class scheduling, group class booking/writeoff, account binding, timeline, audit, idempotency, and role-based access infrastructure. The remaining P0 gaps are private training and reporting: `/private-training` reads Nuxt mock data, `/reports` reads mock summary data, and there are no backend models or real APIs for either capability.

This change should reuse the existing FastAPI, SQLAlchemy, Alembic, PostgreSQL, Nuxt BFF, idempotency, audit, trace ID, and timeline patterns rather than introduce a separate subsystem.

## Goals / Non-Goals

**Goals:**

- Implement a real private training lifecycle from coach availability to member request, coach confirmation/rejection, sign-in, and lesson record.
- Consume private card entitlement when a private booking is confirmed, with transactional safety and timeline/audit traceability.
- Replace mock reporting with real backend report summaries, filters, trends, drill-down details, and Excel export.
- Enforce administrator, coach, and member access boundaries in backend services and endpoints.
- Retire production reliance on mock private training and report BFF routes.

**Non-Goals:**

- WeChat mini-program or public-account H5 delivery is not included; existing Nuxt pages will provide the workflows first.
- SMS/WeChat notification delivery is not included in this change.
- Group class waitlist and QR-code sign-in are not included in this change.
- Background asynchronous export jobs are not required for the first implementation unless synchronous export proves too slow.

## Decisions

### Decision: Model private training as first-class domain tables

Add dedicated tables for private availability, private booking, and private lesson record rather than overloading group class sessions/bookings.

Rationale: private training has different capacity, confirmation, coach ownership, member message, lesson content, and slot-locking semantics. Sharing group class tables would add nullable fields and branching rules to a stable workflow.

Alternative considered: represent private lessons as one-person class sessions. Rejected because coach-published availability and confirmation/rejection would not map cleanly to class session lifecycle.

### Decision: Consume private card entitlement on coach confirmation

Private booking request locks the slot but does not consume entitlement; confirmation consumes exactly one private card time and rejection releases the slot. Pending cancellation by the member or an administrator also releases the slot without any writeoff event.

Rationale: the PRD requires coach confirmation/rejection. Consuming on confirmation avoids charging members for rejected requests while still preventing slot double-booking during review.

Alternative considered: consume on request and refund on rejection. Rejected because it creates more reversal events and a worse member experience for pending requests.

### Decision: Reuse member card and writeoff infrastructure

Private entitlement selection should reuse member card snapshots, card type/scope rules, FEFO ordering, writeoff events, audit logs, idempotency keys, and timeline rendering patterns. Confirmation should call the existing `reserve_hold` writeoff, and private sign-in should call the existing `checkin_commit` writeoff. No new writeoff event type is needed.

Rationale: card consumption and traceability already exist for group classes. Reuse keeps financial and entitlement reconciliation consistent.

Alternative considered: create separate private package balance tables. Rejected because private card products already exist in the card product model.

### Decision: Implement reports as read-only aggregation services plus export endpoint

Create reporting service methods for summary, trends, details, and export. The export endpoint should build `.xlsx` files from the same query inputs used by on-screen drill-down details.

Rationale: reports must reconcile with transactional ledgers and avoid frontend-only calculations. Using one service layer for UI and export reduces mismatch risk.

Alternative considered: export the current frontend table. Rejected because it would preserve mock/cached data risks and bypass access checks.

### Decision: Keep synchronous Excel export initially

Generate filtered Excel exports synchronously for the first implementation, with a 180-day maximum date range and clear service boundaries that can move to an async job later.

Rationale: current expected dataset is modest for administrative filtered reports, and synchronous export avoids adding job queues or storage before there is evidence of need.

Alternative considered: introduce background jobs and export metadata immediately. Deferred to avoid unnecessary infrastructure complexity.

### Decision: Preserve role-aware Nuxt pages rather than create separate apps

Replace current mock pages with role-aware Nuxt views. Members and coaches can access the private training page according to their role; reports remain admin-only.

Rationale: PRD multi-end delivery remains a larger platform concern, but P0 acceptance can be closed in the current web app with real backend workflows.

Alternative considered: build separate H5 routes or app shells now. Deferred because it expands scope beyond the two P0 gaps.

## Risks / Trade-offs

- Private entitlement rules may differ from group class deduction rules -> Keep private writeoff logic explicit and covered by unit tests for confirmation, rejection, sign-in, and conflict cases.
- Synchronous Excel export may become slow for broad date ranges -> Add pagination/detail limits for screen views, stream/download export responses where possible, and keep service boundaries ready for async export later.
- Report totals may diverge from details -> Build summary metrics from the same filters and base queries used by drill-down details; add reconciliation tests for financial totals.
- Slot locking can deadlock or oversell under concurrency -> Use row locks or unique constraints for active slot bookings and idempotency for write operations.
- Reusing writeoff events for private training can make timeline labels ambiguous -> Join writeoff `business_ref` against private bookings before group bookings and render private-specific labels.
- Cross-module scheduling checks can miss edge cases -> Put overlap checks in both private training services and group class scheduling/booking services.

## Migration Plan

1. Add Alembic migration for private availability, private booking, private lesson record, and supporting indexes/constraints.
2. Deploy backend model/service/API changes behind real endpoints while keeping old mock BFF routes untouched until the frontend switches.
3. Replace Nuxt BFF routes and pages to call real private training and report APIs.
4. Remove Mock markers for private training and reports only after real flows and tests pass.
5. Rollback by reverting the frontend to mock routes and leaving unused new tables in place until a follow-up cleanup migration is approved.

## Resolved Questions

- Private booking confirmation consumes exactly one private card time. Consumed hours are reporting metadata only.
- Administrators may confirm, reject, cancel pending, and sign in private bookings on behalf of coaches; all actions are audited.
- Members and administrators may cancel pending private booking requests. Confirmed private bookings cannot be cancelled in this change.
- Excel export is synchronous and limited to date ranges of at most 180 days.
- Weekly availability generation creates non-conflicting slots and returns conflict details for skipped slots.
- Group classes and private training must mutually prevent overlapping member bookings and coach schedules.
