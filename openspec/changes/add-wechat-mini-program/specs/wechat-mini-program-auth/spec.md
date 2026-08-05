## ADDED Requirements

### Requirement: Server-side WeChat code exchange
The system MUST accept a one-time code produced by `wx.login`, exchange it with the configured WeChat service from the FastAPI backend, and MUST NOT expose the Mini Program AppSecret, WeChat `session_key`, or raw OpenID to the Mini Program client.

#### Scenario: Unbound WeChat identity starts a session
- **WHEN** the Mini Program submits a valid `wx.login` code whose WeChat identity is not bound
- **THEN** the system returns an unbound state and a short-lived, single-use binding ticket without issuing an authenticated business token

#### Scenario: Invalid or replayed WeChat code
- **WHEN** the Mini Program submits an invalid, expired, or already consumed login code
- **THEN** the system rejects the exchange without creating an identity binding or returning WeChat secrets

### Requirement: Existing account binding
The system MUST allow an unbound WeChat identity to bind by presenting a valid binding ticket and valid credentials for an existing member or coach account. The system MUST NOT allow administrator accounts to bind through the Mini Program.

Each WeChat identity within the configured AppID MUST bind to at most one business account, and each business account MUST bind to at most one WeChat identity for that AppID. Binding MUST preserve the existing member or coach profile relationship instead of creating a duplicate profile.

#### Scenario: Member binds an existing account
- **WHEN** an unbound WeChat identity presents a valid binding ticket and correct credentials for an enabled member login
- **THEN** the system atomically binds the identity to that account and issues a JWT containing the account role and `memberId`

#### Scenario: Coach binds an existing account
- **WHEN** an unbound WeChat identity presents a valid binding ticket and correct credentials for an enabled coach login
- **THEN** the system atomically binds the identity to that account and issues a JWT containing the account role and `coachProfileId`

#### Scenario: Identity or account is already bound elsewhere
- **WHEN** a binding request would bind one WeChat identity to multiple accounts or one account to multiple identities for the same AppID
- **THEN** the system returns a conflict and preserves the existing binding

#### Scenario: Administrator attempts Mini Program binding
- **WHEN** valid administrator credentials are submitted with a binding ticket
- **THEN** the system rejects the binding and does not issue a Mini Program business token

### Requirement: Bound identity login
The system MUST issue the existing FastAPI Bearer JWT format when a valid WeChat code resolves to a bound member or coach account. The JWT MUST derive role and business resource identifiers from the current account record, not from client input or stale binding metadata.

#### Scenario: Bound member returns to the Mini Program
- **WHEN** a valid WeChat code resolves to a bound, login-eligible member account
- **THEN** the system issues a member JWT with the current `memberId` without requesting the account password again

#### Scenario: Bound coach returns to the Mini Program
- **WHEN** a valid WeChat code resolves to a bound, enabled coach account
- **THEN** the system issues a coach JWT with the current `coachProfileId` without requesting the account password again

### Requirement: Account status remains authoritative
The system MUST apply the existing member and coach login-status rules on initial binding and every subsequent WeChat login. Disabling, deleting, or otherwise making an account ineligible MUST prevent new JWT issuance even when its WeChat binding remains recorded.

#### Scenario: Bound coach is disabled
- **WHEN** a WeChat identity bound to a disabled coach submits a valid login code
- **THEN** the system refuses login and returns an actionable account-disabled result

#### Scenario: Bound member is deleted or disabled
- **WHEN** a WeChat identity bound to a deleted or disabled member submits a valid login code
- **THEN** the system refuses login and does not expose member data

### Requirement: Administrator-controlled identity recovery
The system MUST allow an administrator to inspect whether a member or coach account has a WeChat binding and to remove that binding without exposing the raw OpenID. Unbinding MUST require an explicit confirmation, MUST be audited, and MUST immediately prevent the removed identity from obtaining new business tokens for that account.

The initial release MUST implement recovery as unbind followed by the standard first-use binding flow. It MUST NOT silently transfer a binding directly between accounts or WeChat identities.

#### Scenario: Administrator unbinds an incorrectly bound member account
- **WHEN** an administrator confirms unbinding for a member account with an existing WeChat identity
- **THEN** the system removes the binding, records the administrator and affected account in the audit trail, and permits a later standard binding with valid credentials

#### Scenario: Administrator requests unbinding for an unbound account
- **WHEN** an administrator requests unbinding for an account that has no current WeChat identity
- **THEN** the system returns an explicit not-bound result and creates no misleading successful audit event

#### Scenario: Non-administrator attempts to unbind an account
- **WHEN** a member or coach calls the administrator unbind operation
- **THEN** the system returns 403, preserves the binding, and records the rejected privileged action

### Requirement: Mini Program token lifecycle
The Mini Program MUST send authenticated API requests with the issued Bearer token, clear unusable tokens after authentication failure, and restart WeChat login before retrying protected operations. It MUST NOT place the token in page URLs, logs, analytics events, or user-visible error messages.

#### Scenario: Stored token expires
- **WHEN** a protected API request returns an authentication failure for the stored Mini Program token
- **THEN** the client clears the token, obtains a new `wx.login` code, and restores the session only if the bound account remains eligible

### Requirement: WeChat authentication auditing and throttling
The system MUST audit successful bindings, binding conflicts, and rejected Mini Program authentication attempts without recording credentials, tokens, `session_key`, or full WeChat identifiers. Credential binding attempts MUST be rate-limited by identity and network source.

#### Scenario: Repeated incorrect binding credentials
- **WHEN** an unbound identity repeatedly submits incorrect account credentials
- **THEN** the system throttles further attempts, records a security event, and does not reveal whether the username exists
