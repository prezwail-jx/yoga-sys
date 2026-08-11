## 1. Baseline And External Gates

- [x] 1.1 Complete and verify `improve-account-member-admin-flows`, including password reset, disabled-member recovery, account audit coverage, and final account-model compatibility
- [x] 1.2 Run and record the current private-training/reporting backend and frontend acceptance checks so migration `0007` and the APIs consumed by the Mini Program are a stable baseline
- [x] 1.3 Verify ownership, DNS control, ICP备案, and the public server for `yoga.tuitukj.com`, and document the remaining TLS, reverse-proxy, PostgreSQL backup, and FastAPI deployment work
- [x] 1.4 Record non-personal subject registration as a deferred production prerequisite; do not treat the current personal-only subject or development build as a commercial release target
- [x] 1.5 Record service-category, qualification, privacy, and member-card review checks as deferred production gates to verify in the actual non-personal WeChat management console
- [x] 1.6 Record development and production AppIDs, API hostnames, secret-management mechanism, access-token lifetime, binding-challenge lifetime, and feature-flag strategy without committing secrets

## 2. WeChat Identity And Challenge Persistence

- [x] 2.1 Add a `wechat_identity` model linked to `admin_user` with AppID, HMAC OpenID digest, binding metadata, and timestamps, without persisting raw OpenID or `session_key`
- [x] 2.2 Add constraints for unique `(appid, openid_digest)` and unique `(appid, account_id)` bindings and define deterministic conflict responses
- [x] 2.3 Add a `wechat_binding_challenge` model with opaque-ticket digest, AppID, OpenID digest, expiry, consumed time, failed-attempt count, and source fingerprint
- [x] 2.4 Add the next Alembic migration after the verified `0007` baseline and test upgrade/downgrade without changing existing account or browser-authentication data
- [x] 2.5 Implement repository operations for identity lookup, challenge creation/consumption, atomic binding, unbinding, expiry cleanup, and row/advisory locking under concurrent requests
- [x] 2.6 Add PostgreSQL integration tests for identity uniqueness, ticket replay, expiry, concurrent binding, unbinding, and preservation of existing accounts

## 3. Backend WeChat Authentication

- [x] 3.1 Add validated environment configuration for AppID, AppSecret, `WECHAT_IDENTITY_PEPPER`, provider timeout, challenge policy, token lifetime, and production enablement
- [x] 3.2 Implement an injectable fake provider for automated/local tests and a real WeChat code-exchange provider with explicit timeout and mapped provider errors
- [x] 3.3 Implement `POST /auth/wechat/session` for unbound, bound-member, bound-coach, invalid-code, disabled-account, and provider-failure outcomes
- [x] 3.4 Implement `POST /auth/wechat/bind` with challenge locking/consumption, uniform credential errors, member/coach status checks, administrator rejection, atomic binding, and standard JWT issuance
- [x] 3.5 Reuse one account eligibility and claim-building path for password login and WeChat login so role, `memberId`, and `coachProfileId` cannot diverge
- [x] 3.6 Add challenge-level attempt limits plus source-level gateway/application throttling, and redact AppSecret, password, JWT, ticket, raw OpenID, and `session_key` from logs and traces
- [x] 3.7 Record audits for successful binding, conflicts, disabled-account attempts, ticket abuse, and rejected authentication without storing sensitive values
- [x] 3.8 Add backend tests for provider exchange, HMAC lookup, ticket lifecycle, all roles/statuses, duplicate bindings, throttling, claim contents, and sensitive-data redaction
- [x] 3.9 Re-run existing password login, account binding, RBAC, and Nuxt cookie/BFF tests to prove browser authentication remains unchanged

## 4. Administrator Binding Recovery

- [x] 4.1 Add an administrator-only binding-status query that reports bound/unbound state without returning raw OpenID
- [x] 4.2 Add `DELETE /accounts/{accountId}/wechat-binding` with explicit not-bound handling, row locking, authorization, trace ID, and append-only audit recording
- [x] 4.3 Add member and coach account-management UI controls in Nuxt for binding status, explicit unbind confirmation, success/error feedback, and no direct transfer action
- [x] 4.4 Add backend and frontend tests for member unbind, coach unbind, unbound account, non-administrator rejection, audit contents, and successful standard rebinding

## 5. Member Self-Service API Extensions

- [x] 5.1 Add a dedicated read-only member-card response schema that omits refundable transaction IDs, audit data, and administrator lifecycle controls
- [x] 5.2 Add `GET /members/me/cards`, deriving `memberId` only from the JWT and returning current status, remaining sessions, activation/expiry, and freeze information
- [x] 5.3 Add tests for normal, paused, expired, frozen, duration, session, private, trial, and empty card results plus cross-member isolation

## 6. Coach Availability API Reliability

- [x] 6.1 Verify existing private-slot service ownership, enabled-coach, overlap, group-class conflict, locked-slot, and active-booking rules against Mini Program scenarios
- [x] 6.2 Add optional `Idempotency-Key` replay support to single-slot create, update, and cancel endpoints while keeping existing Nuxt callers without the header compatible
- [x] 6.3 Verify week generation continues to require idempotency and returns created items plus explicit conflicts
- [x] 6.4 Add integration tests for replayed create/update/cancel, uncertain retries, cross-coach access, locked-slot cancellation, and browser compatibility

## 7. Native Mini Program Foundation

- [x] 7.1 Create the native TypeScript `miniapp/` workspace with WXML/WXSS, project configuration, environment-specific API base URLs, linting, type checking, tests, and ignored local settings
- [x] 7.2 Implement the `wx.request` client with Bearer headers, trace propagation, normalized backend errors, timeouts, and sensitive-data-safe logging
- [x] 7.3 Implement idempotency-key creation and persistence so uncertain retries reuse the key while changed user operations receive a new key
- [x] 7.4 Implement token storage, startup restoration, terminal 401 cleanup, `wx.login` recovery, and current-user loading
- [x] 7.5 Implement first-use account binding with ticket expiry, duplicate-submit prevention, uniform credential errors, and no password persistence
- [x] 7.6 Implement server-derived member/coach navigation, account/session page, logout, forbidden-role handling, and native loading/empty/error/retry components
- [x] 7.7 Add client tests for API headers, error mapping, token recovery, binding transitions, ticket expiry, idempotency retries, and role routing

## 8. Member Mini Program

- [x] 8.1 Implement chronological day-group class schedules with week navigation, capacity, booking state, and loading/empty/error/retry states
- [x] 8.2 Implement class booking with confirmation, pending suppression, retained idempotency key, backend eligibility feedback, and authoritative refresh
- [x] 8.3 Implement paginated class-booking history and eligible cancellation with cutoff messaging, optional reason, idempotency, and authoritative refresh
- [x] 8.4 Implement private-slot browsing, private request creation with optional message, private-booking history, and pending-request cancellation
- [x] 8.5 Implement the read-only member-card page with product/type, status, remaining sessions, validity, freeze information, and no purchase or lifecycle actions
- [x] 8.6 Add member client tests for schedule grouping, class/private mutations, card presentation, duplicate taps, pagination, empty/error states, and role isolation
- [x] 8.7 Add end-to-end API tests proving member tokens can access only their own bookings and cards and cannot select another member identity

## 9. Coach Mini Program

- [x] 9.1 Implement assigned class schedules as mobile day groups with course, room, time, status, capacity, and booked count
- [x] 9.2 Implement assigned-session rosters and eligible group-class check-in with confirmation, idempotency, timing/status feedback, and authoritative refresh
- [x] 9.3 Implement private availability listing, single-slot creation/edit/cancellation, and weekly generation with conflict display and idempotency-safe retries
- [x] 9.4 Implement private workload views separating pending, confirmed, completed, rejected, and cancelled bookings
- [x] 9.5 Implement private request confirmation/rejection and confirmed-lesson sign-in with required record fields, validation, idempotency, and authoritative refresh
- [x] 9.6 Add coach client tests for assigned classes, check-in, availability ownership/conflicts, private decisions, lesson validation, uncertain retries, and role isolation
- [x] 9.7 Add end-to-end API tests proving coaches can access and mutate only assigned class and private resources and that rejected cross-coach access is audited

## 10. Automated Security And Regression Gates

- [x] 10.1 Verify repeated and concurrent Mini Program mutations preserve booking, writeoff, private-training, row-lock, and idempotency invariants
- [x] 10.2 Scan source, responses, logs, traces, and client storage to verify AppSecret, password, JWT, raw ticket, raw OpenID, and `session_key` are not exposed outside their intended boundary
- [x] 10.3 Run backend unit, PostgreSQL integration, migration, OpenAPI, lint, and type checks and resolve regressions attributable to this change
- [x] 10.4 Run Mini Program lint, type checks, unit tests, page/component interaction tests, and production package build
- [x] 10.5 Run existing Nuxt unit, Playwright, lint, typecheck, and production build suites to confirm administrator and browser workflows remain operational

## 11. Production Infrastructure And Real-Device Release Gates

- [x] 11.1 Treat this entire section as a deferred production milestone; it is not required to declare the fake-provider/local-backend development build complete
- [ ] 11.2 Provision a public application server, complete or confirm ICP备案, configure DNS, valid TLS, reverse proxy, PostgreSQL backup, and a production FastAPI health check
- [ ] 11.3 Register the exact HTTPS API hostname as a WeChat request legal domain and verify production AppID plus secrets are loaded from the approved secret store
- [ ] 11.4 Complete non-personal subject verification, approved service category, privacy disclosures, and any qualification materials required by the WeChat console
- [ ] 11.5 Replace the fake provider with real `code2Session` integration and verify binding, returning login, expiry recovery, unbind/rebind, member flows, and coach flows on real iOS and Android WeChat clients
- [ ] 11.6 Verify disabled/deleted member, disabled coach, wrong credentials, expired ticket, no entitlement, capacity conflict, cutoff, cross-role access, and interrupted-network cases
- [ ] 11.7 Publish to an internal WeChat trial group, record acceptance evidence and observed authentication/business error rates, and validate rollback by disabling WeChat authentication without affecting Nuxt access
- [ ] 11.8 Submit the scoped member-and-coach Mini Program for review only after all qualification, infrastructure, automated, and real-device gates pass
