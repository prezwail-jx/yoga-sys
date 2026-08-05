## ADDED Requirements

### Requirement: Real business report summary
The system SHALL provide real report summary data from persisted business records instead of mock data. The summary SHALL include total members, active members, expiring members, card sales, renewal income, refund amount, group class attendance rate, group class full-rate, private lesson count, private consumed hours, and private completion rate.

Active members SHALL mean non-archived members whose status is `normal`. Expiring members SHALL mean members with active cards expiring within the next 7 days. Group class attendance rate SHALL be calculated from completed sessions as `checked_in / (checked_in + absent)`. Group class full-rate SHALL be calculated from completed sessions whose final checked-in plus absent count reaches capacity.

Summary queries SHALL support date range filters and SHALL only be available to administrators unless a narrower role-specific report is explicitly requested.

#### Scenario: Administrator views report summary
- **WHEN** an administrator opens the reports page with a date range
- **THEN** the system returns summary metrics calculated from members, cards, transactions, group class bookings, and private training records within that range

#### Scenario: Member reads admin summary
- **WHEN** a member requests the administrator report summary endpoint
- **THEN** the system returns 403 and records a rejected access audit event

### Requirement: Report dimension filters and trends
The system SHALL support report filtering by date range, coach, course, card product, and report category where applicable. The system SHALL provide trend data suitable for charting revenue, bookings, attendance, and private lesson completion over time.

Filters SHALL be validated against existing records and SHALL not silently include unrelated data.

#### Scenario: Filter course attendance by coach and course
- **WHEN** an administrator requests course attendance metrics with coach and course filters
- **THEN** the system returns only matching class sessions and bookings in the selected date range

#### Scenario: Request revenue trend
- **WHEN** an administrator requests revenue trend data grouped by day
- **THEN** the system returns ordered trend points derived from purchase, renewal, reissue, refund, and extension transactions as applicable

### Requirement: Report detail drill-down
The system SHALL provide drill-down detail results for summary metrics that represent members, transactions, class bookings, private bookings, or refunds. Detail results SHALL include enough identifiers for the UI to navigate to the relevant member, class session, private booking, or transaction record.

Detail queries SHALL support pagination and SHALL preserve the same filters used by the summary metric.

#### Scenario: Drill down expiring members
- **WHEN** an administrator opens the detail list for expiring members
- **THEN** the system returns paginated member-card rows including member, card, remaining entitlement, and expiry information

#### Scenario: Drill down refunds
- **WHEN** an administrator opens the refund detail list for a date range
- **THEN** the system returns paginated refund transactions with member, card, amount, reason, and transaction time

### Requirement: Excel report export
The system SHALL allow administrators to export supported reports to Excel using the currently selected filters. Exported files SHALL include the report name, filter metadata, generated timestamp, and tabular detail rows matching the on-screen report data.

Exports SHALL be generated from server-side data and SHALL not depend on frontend-only mock or cached rows. Synchronous exports SHALL reject date ranges longer than 180 days.

#### Scenario: Export filtered report
- **WHEN** an administrator exports a report after applying date, coach, and course filters
- **THEN** the system downloads an `.xlsx` file whose rows match the filtered report details

#### Scenario: Unauthorized export request
- **WHEN** a coach or member requests an administrator report export
- **THEN** the system returns 403 and does not generate an export file

#### Scenario: Export date range too large
- **WHEN** an administrator requests an Excel export for a date range longer than 180 days
- **THEN** the system returns 422 and does not generate an export file

### Requirement: Reporting consistency and traceability
The system SHALL calculate reports from transactional ledgers, bookings, writeoff events, and lesson records so that summary totals reconcile with detail drill-down rows. Report requests SHALL include trace IDs and SHALL avoid mutating business state.

#### Scenario: Summary reconciles with details
- **WHEN** an administrator compares card sales summary with the corresponding transaction detail drill-down for the same filters
- **THEN** the sum of detail rows equals the summary amount within currency rounding rules
