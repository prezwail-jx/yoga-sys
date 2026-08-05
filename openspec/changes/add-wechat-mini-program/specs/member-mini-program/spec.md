## ADDED Requirements

### Requirement: Member-native navigation
The Mini Program MUST provide a member workspace with native navigation for class schedule, private training, personal bookings, member cards, and account/session actions. It MUST derive the workspace role from the authenticated server response and MUST NOT expose coach or administrator actions to a member.

#### Scenario: Member enters the Mini Program
- **WHEN** an authenticated member session is established
- **THEN** the client opens the member workspace and displays only member-authorized destinations and operations

### Requirement: Member group-class schedule
The Mini Program MUST allow a member to browse authorized group-class sessions by week and day, including local date and time, course, coach, room, capacity, remaining places, status, and booking availability. Mobile presentation MUST use a day-oriented list rather than requiring a seven-column desktop layout.

#### Scenario: Member views a week with published sessions
- **WHEN** a member selects a natural week
- **THEN** the client displays its authorized sessions in chronological day groups with current capacity and booking state

#### Scenario: Schedule request fails
- **WHEN** the schedule cannot be loaded because of a network or server failure
- **THEN** the client displays an actionable error and permits an explicit retry without showing stale data as current

### Requirement: Member group-class booking
The Mini Program MUST allow a member to book an eligible session and cancel their own eligible reservation using an idempotency key per submitted operation. The backend MUST continue enforcing the existing booking window, capacity, membership, card entitlement, conflict, cancellation, and writeoff requirements.

#### Scenario: Member books an eligible session
- **WHEN** a member confirms booking for a session that passes backend eligibility checks
- **THEN** the client submits one idempotent booking operation and refreshes the session and personal booking state from the server

#### Scenario: Member cancels before the cutoff
- **WHEN** a member confirms cancellation of their reservation before its cancellation cutoff
- **THEN** the client submits one idempotent cancellation operation and displays the resulting cancelled state and server outcome

#### Scenario: Backend rejects booking eligibility
- **WHEN** the backend rejects a booking because of capacity, time window, conflict, member status, or card entitlement
- **THEN** the client displays the actionable backend reason and does not optimistically retain a booked state

### Requirement: Member private-training booking
The Mini Program MUST allow a member to browse currently available private-training slots, submit a request for themselves with an optional message, list their own requests, and cancel their own pending request. All eligibility, locking, conflict, entitlement, and lifecycle decisions MUST remain authoritative in the existing private-training backend.

#### Scenario: Member requests an available private slot
- **WHEN** a member confirms an available slot and optionally enters a coach message
- **THEN** the client submits one idempotent request and displays the server-returned pending booking

#### Scenario: Member cancels a pending private request
- **WHEN** a member cancels their own pending private-training request
- **THEN** the client submits one idempotent cancellation and refreshes the slot and booking lists

### Requirement: Member personal booking history
The Mini Program MUST provide paginated views of the authenticated member's group-class and private-training bookings, including status, date, coach, location when applicable, and available next actions. The client MUST NOT accept or send an arbitrary member identifier for self-service queries.

#### Scenario: Member views personal bookings
- **WHEN** a member opens the personal bookings destination
- **THEN** the system returns and displays only bookings associated with the `memberId` in the authenticated token

#### Scenario: No personal bookings exist
- **WHEN** the authenticated member has no bookings in the selected category
- **THEN** the client displays an empty state with a route to the applicable schedule or private-training view

### Requirement: Member read-only card visibility
The Mini Program MUST allow an authenticated member to view only their own cards with product name, card type, current status, remaining sessions when applicable, activation date, expiry date, and freeze period when applicable. The self-service response MUST NOT expose administrator-only transaction, refund, internal audit, or lifecycle-control fields.

The member-card view MUST be read-only in the initial release and MUST NOT offer purchase, renewal, refund, extension, freeze, or unfreeze operations.

#### Scenario: Member views their usable cards
- **WHEN** an authenticated member opens the member-card destination
- **THEN** the system derives `memberId` from the token and returns only that member's cards with current balance and validity information

#### Scenario: Member has no cards
- **WHEN** the authenticated member has no card records
- **THEN** the client displays an empty state without offering payment or administrator lifecycle actions

#### Scenario: Member attempts to query another member's cards
- **WHEN** a member submits or manipulates a request to select another member identifier
- **THEN** the system does not accept the client-selected identity, returns no other member card data, and records rejected cross-member access when an identifier-based administrator route is attempted

### Requirement: Member operation feedback
The Mini Program MUST prevent duplicate submissions while an operation is pending and MUST present loading, success, empty, authentication, authorization, conflict, and retryable failure states in native pages.

#### Scenario: Member taps a pending action repeatedly
- **WHEN** a booking or cancellation request is already in flight and the member taps its action again
- **THEN** the client suppresses duplicate submissions while the backend idempotency key protects any transport retry
