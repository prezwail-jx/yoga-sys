## ADDED Requirements

### Requirement: Coach-native navigation
The Mini Program MUST provide a coach workspace with native navigation for assigned classes, attendance work, private availability, private-training requests, and account/session actions. It MUST derive the workspace role from the authenticated server response and MUST NOT expose member self-booking or administrator operations to a coach.

#### Scenario: Coach enters the Mini Program
- **WHEN** an authenticated coach session is established
- **THEN** the client opens the coach workspace and displays only coach-authorized destinations and operations

### Requirement: Coach assigned schedule
The Mini Program MUST show only group-class sessions assigned to the authenticated coach, organized for mobile use by day and start time. Each session MUST show course, room, time, status, capacity, and booked count, with access to its authorized attendance work.

#### Scenario: Coach views assigned classes
- **WHEN** a coach opens a selected day or week
- **THEN** the system returns and displays only sessions whose `coachProfileId` matches the authenticated token

#### Scenario: Coach attempts to access another coach session
- **WHEN** a coach requests attendance details for a session assigned to another coach
- **THEN** the system returns 403, records the rejected access, and the client does not display its roster

### Requirement: Coach class attendance
The Mini Program MUST allow the assigned coach to view the authorized attendee roster and check in eligible reservations using an idempotency key. Existing check-in window, session status, booking terminal-state, writeoff, and audit requirements MUST remain authoritative in the backend.

#### Scenario: Assigned coach checks in a member
- **WHEN** the assigned coach confirms check-in for an eligible reservation within the allowed window
- **THEN** the client submits one idempotent check-in operation and refreshes the roster with the server-returned checked-in state

#### Scenario: Check-in is no longer allowed
- **WHEN** the backend rejects check-in because the booking or session is ineligible
- **THEN** the client displays the backend reason and preserves the authoritative roster state

### Requirement: Coach private-training workload
The Mini Program MUST list only private-training bookings belonging to the authenticated coach and MUST distinguish pending requests, confirmed lessons, and completed or rejected history.

#### Scenario: Coach views pending private requests
- **WHEN** a coach opens the pending private-training destination
- **THEN** the system returns only pending requests for that coach profile with the member, slot, and optional request message needed for a decision

### Requirement: Coach private availability management
The Mini Program MUST allow an authenticated coach to list, create, update, generate by week, and cancel only their own private-training availability. The backend MUST continue enforcing ownership, enabled-coach status, future-time, overlap, locked-slot, group-class conflict, and active-booking rules.

Mini Program create, update, week-generation, and cancellation submissions MUST use idempotency keys. Existing browser callers that do not yet send keys MUST remain compatible during migration.

#### Scenario: Coach publishes a private slot
- **WHEN** a coach submits a valid future slot that does not overlap their active group classes or private availability
- **THEN** the system creates one availability record owned by the authenticated `coachProfileId` and the client refreshes the coach's availability list

#### Scenario: Coach generates a week of availability
- **WHEN** a coach submits a valid weekly pattern with an idempotency key
- **THEN** the system returns created slots and explicit conflicts without duplicating slots when the same operation is replayed

#### Scenario: Coach updates their available slot
- **WHEN** a coach changes an unlocked future slot that has no active booking
- **THEN** the system updates that slot after rechecking time and group-class conflicts

#### Scenario: Coach cancels a locked slot
- **WHEN** a coach attempts to cancel a slot with an active pending or confirmed booking
- **THEN** the system rejects the cancellation and preserves the booking lifecycle

#### Scenario: Coach modifies another coach's slot
- **WHEN** a coach attempts to create, update, or cancel availability for another coach profile
- **THEN** the system returns 403 and records the rejected access

### Requirement: Coach private-training decisions
The Mini Program MUST allow the owning coach to confirm or reject a pending private-training request using one idempotency key per decision. Rejection MUST allow the reason supported by the existing private-training contract, and backend lifecycle and entitlement rules MUST remain authoritative.

#### Scenario: Coach confirms a pending request
- **WHEN** the owning coach confirms a pending private-training request
- **THEN** the client submits one idempotent confirmation and displays the server-returned confirmed state

#### Scenario: Coach rejects a pending request
- **WHEN** the owning coach submits a rejection with an optional reason
- **THEN** the client submits one idempotent rejection and displays the server-returned rejected state

### Requirement: Coach private-lesson sign-in
The Mini Program MUST allow the owning coach to sign in a confirmed private booking with lesson content, consumed hours, and member status notes required by the existing private-training contract. It MUST prevent duplicate submission while pending and use an idempotency key for transport retries.

#### Scenario: Coach completes a private lesson
- **WHEN** the owning coach submits valid lesson information for a confirmed private booking
- **THEN** the client submits one idempotent sign-in operation and displays the completed booking and saved lesson result

#### Scenario: Lesson information is invalid
- **WHEN** required lesson information is missing or rejected by backend validation
- **THEN** the client identifies the invalid fields or server reason and does not display the booking as completed

### Requirement: Coach operation feedback
The Mini Program MUST present loading, success, empty, authentication, authorization, conflict, and retryable failure states for coach pages and MUST refresh authoritative data after every successful mutation.

#### Scenario: Coach mutation has an uncertain network result
- **WHEN** the connection fails after an idempotent coach operation was submitted
- **THEN** the client may retry with the same idempotency key and then refreshes the resource instead of assuming success or failure
