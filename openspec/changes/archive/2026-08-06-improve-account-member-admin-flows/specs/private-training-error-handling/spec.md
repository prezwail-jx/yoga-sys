## ADDED Requirements

### Requirement: Private-training actionable errors
The system SHALL return actionable, role-appropriate error messages for expected private-training failures, including unauthenticated access, forbidden role/resource access, validation errors, scheduling conflicts, duplicate or locked slots, insufficient entitlement, and invalid booking status transitions.

Unexpected server errors SHALL remain generic to the end user but SHALL include or preserve a trace ID for operator diagnosis.

#### Scenario: Create private slot with invalid input
- **WHEN** a coach or administrator submits a private slot with an invalid time range or missing required coach selection
- **THEN** the system returns a 422 or 409 response with a clear error reason, and the frontend displays a user-readable Chinese message

#### Scenario: Create private slot with schedule conflict
- **WHEN** a coach or administrator creates a private slot overlapping an active private slot or assigned group class
- **THEN** the system rejects the request with a conflict response and the frontend explains the conflict

#### Scenario: Member books unavailable private slot
- **WHEN** a member requests a locked, cancelled, past, or otherwise unavailable private slot
- **THEN** the system rejects the request without creating a booking and the frontend displays an actionable reason

#### Scenario: Unexpected private-training server error
- **WHEN** an unexpected backend exception occurs during private-training operations
- **THEN** the frontend shows a generic failure message and exposes enough trace context for operator troubleshooting

### Requirement: Private-training smoke coverage
The system SHALL include backend and frontend coverage for private-training create/list and booking lifecycle operations so regressions do not surface only during manual UI testing.

#### Scenario: Private-training backend smoke tests
- **WHEN** automated backend checks run
- **THEN** private slot create/list, booking create/list, confirm, reject, cancel, and sign-in paths are covered by smoke or integration tests

#### Scenario: Private-training frontend E2E tests
- **WHEN** automated frontend E2E checks run
- **THEN** creating a slot and handling common private-training errors are covered
