## Why

The current product still has two P0 gaps against `docs/prd.md`: private training is mock-only, and reports are mock-only with no export. Completing these closes the remaining must-have acceptance gaps for private lesson booking and query/statistics/export.

## What Changes

- Replace the mock private training page and BFF data with a real private training workflow backed by PostgreSQL.
- Allow coaches to publish private availability by day or week, including slot duration and automatic locking after booking.
- Allow members to browse coaches and available slots, submit private bookings with an optional message, and track booking status.
- Allow coaches to confirm or reject private bookings, sign in completed lessons, and record lesson content, consumed hours, and member status.
- Allow members and administrators to cancel pending private booking requests before coach confirmation; cancellation releases the locked slot without consuming entitlement.
- Deduct private card entitlement when a private booking is confirmed, prevent duplicate booking of locked slots, and preserve writeoff/audit history.
- Prevent cross-module time conflicts between group classes and private training for both members and coaches.
- Replace mock reports with real reporting APIs for member, card, course, private training, and financial metrics.
- Add report filters, drill-down detail APIs/pages where needed, trend data, and Excel export.
- Remove or retire the mock-only private training and report API usage from production navigation flows.

## Capabilities

### New Capabilities

- `private-training`: Coach availability publishing, member private booking, coach confirmation/rejection, slot locking, private lesson sign-in, lesson records, and private card entitlement consumption.
- `business-reporting`: Real operational, course, private training, card, member, and financial reporting with filters, trends, detail drill-down, and Excel export.

### Modified Capabilities

- `class-scheduling`: Prevent coaches from being scheduled for group classes that overlap active private training slots or bookings.
- `class-booking-writeoff`: Prevent members from booking group classes that overlap active private training bookings.

## Impact

- Backend: new private training domain models, migrations, services, schemas, routers, reporting aggregation services, and Excel export support.
- Frontend: replace `/private-training` and `/reports` mock pages with role-aware real workflows and reporting UI; add API client methods and BFF proxy routes.
- Data: new tables for private availability, private bookings, private lesson records, and any export/job metadata if needed.
- Auth and permissions: admin, coach, and member access must be enforced at backend level; members only access their own bookings and records, coaches only access their own private workload.
- Observability and compliance: critical writes require idempotency where applicable, transaction boundaries, audit logs, trace IDs, and tests.
