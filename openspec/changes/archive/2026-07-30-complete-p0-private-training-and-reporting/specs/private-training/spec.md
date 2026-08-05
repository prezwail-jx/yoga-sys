## ADDED Requirements

### Requirement: Coach availability publishing
The system SHALL allow an authenticated coach to publish, update, and cancel only their own private training availability slots. The system SHALL allow an administrator to manage availability for any coach.

Availability SHALL support day-based and week-based creation, configurable slot duration, start/end times, and overlap validation. Published slots SHALL be visible to members only when the coach is enabled and the slot is not locked, cancelled, or in the past.

#### Scenario: Coach publishes weekly availability
- **WHEN** a coach submits a valid weekly availability pattern for their own coach profile
- **THEN** the system creates private availability slots for that coach and rejects any slots that overlap existing active availability

#### Scenario: Coach edits another coach availability
- **WHEN** a coach attempts to edit an availability slot owned by another coach
- **THEN** the system returns 403 and records a rejected access audit event

### Requirement: Member private training booking
The system SHALL allow a member to browse enabled coaches and available private training slots, submit a booking for themselves, and include an optional message for the coach.

The system SHALL validate member status, usable private card entitlement, slot availability, duplicate bookings, time conflicts, and idempotency before creating a booking. A requested booking SHALL lock the selected slot so it cannot be booked by another member while the request is active.

The system SHALL reject private booking requests that overlap an active group class booking for the same member.

#### Scenario: Member requests an available private slot
- **WHEN** a logged-in normal member requests an unlocked future private slot with usable private card entitlement
- **THEN** the system creates a pending private booking, stores the member message when provided, and locks the slot

#### Scenario: Two members request the same slot concurrently
- **WHEN** two members concurrently request the same unlocked private slot
- **THEN** only one booking is created and the other request is rejected without consuming entitlement

#### Scenario: Member has overlapping group class booking
- **WHEN** a logged-in member requests a private slot that overlaps one of their active group class bookings
- **THEN** the system rejects the private booking request and keeps the slot available

### Requirement: Pending private booking cancellation
The system SHALL allow the booking member or an administrator to cancel a pending private booking request before coach confirmation. Cancelling a pending private booking SHALL release the locked slot and SHALL NOT consume or refund card entitlement.

Coaches SHALL reject pending private bookings instead of using cancellation, so rejection reason and coach decision history remain explicit.

#### Scenario: Member cancels pending private booking
- **WHEN** a member cancels their own pending private booking request
- **THEN** the booking becomes cancelled, the slot becomes available, and no writeoff event is created

#### Scenario: Administrator cancels pending private booking
- **WHEN** an administrator cancels any pending private booking request with an optional reason
- **THEN** the booking becomes cancelled, the slot becomes available, and the action is audited

### Requirement: Coach confirmation and rejection
The system SHALL allow the owning coach or an administrator to confirm or reject pending private bookings. Confirmation SHALL consume exactly one private card time according to FEFO card selection and private card rules, and rejection SHALL release the locked slot without consuming entitlement.

Confirmation and rejection SHALL be terminal for the pending decision and SHALL be protected by idempotency keys.

#### Scenario: Coach confirms private booking
- **WHEN** the owning coach confirms a pending private booking
- **THEN** the booking becomes confirmed, the slot remains locked, and a `reserve_hold` writeoff event deducts one private card time

#### Scenario: Coach rejects private booking
- **WHEN** the owning coach rejects a pending private booking with an optional reason
- **THEN** the booking becomes rejected, the slot is released, and no private card entitlement is consumed

### Requirement: Private lesson sign-in and record
The system SHALL allow the owning coach or an administrator to sign in a confirmed private booking and create a lesson record with lesson content, consumed hours, and member status notes.

Private sign-in SHALL be allowed only for confirmed bookings and SHALL preserve an immutable audit and timeline trail for the member. Private sign-in SHALL create a `checkin_commit` writeoff event, while consumed hours SHALL be used for reporting only and SHALL NOT change the number of consumed card times.

#### Scenario: Coach signs in private lesson
- **WHEN** the owning coach signs in a confirmed private booking with lesson content, consumed hours, and member status notes
- **THEN** the system marks the booking completed, saves the lesson record, and exposes the event in the member business timeline

#### Scenario: Sign in unconfirmed private booking
- **WHEN** an operator attempts to sign in a pending or rejected private booking
- **THEN** the system rejects the request and does not create a lesson record

### Requirement: Private training access boundaries
The system SHALL enforce role-based access for all private training data. Members SHALL access only their own private bookings and lesson records; coaches SHALL access only their own availability, private bookings, and lesson records; administrators SHALL access all private training data.

#### Scenario: Member reads another member private booking
- **WHEN** a member requests a private booking or lesson record owned by another member
- **THEN** the system returns 403 and records a rejected access audit event

#### Scenario: Coach lists private workload
- **WHEN** a coach lists private training bookings
- **THEN** the system returns only bookings associated with that coach profile

### Requirement: Coach schedule conflict prevention
The system SHALL reject private availability slots that overlap active group class sessions assigned to the same coach, and SHALL reject group class scheduling changes that overlap active private availability or bookings for the same coach.

#### Scenario: Coach publishes slot overlapping group class
- **WHEN** a coach publishes a private availability slot that overlaps their assigned active group class session
- **THEN** the system rejects the private availability slot and returns a conflict reason

#### Scenario: Administrator schedules group class overlapping private slot
- **WHEN** an administrator creates or updates a group class session for a coach during an active private availability or booking window
- **THEN** the system rejects the group class scheduling change
