## Context

The current application is a Nuxt 3 browser client and Nitro BFF backed by FastAPI and PostgreSQL. Browser authentication stores a FastAPI JWT in an HttpOnly `yoga_token` cookie; Nitro routes recover that cookie and call FastAPI with a Bearer token. The same Nuxt pages currently branch by administrator, coach, and member roles, but their desktop navigation and combined role workflows are not suitable as a native Mini Program interface.

FastAPI already owns authoritative RBAC and places `memberId` or `coachProfileId` in JWT claims. Existing class-booking and private-training services enforce entitlement, conflicts, idempotency, and audit rules, so the new client must reuse those services rather than reproduce business decisions. WeChat adds an external code-exchange service, platform domain restrictions, secrets, and a persistent identity mapping.

The active `improve-account-member-admin-flows` change also affects account and authentication code. Implementation of this change must inspect and reconcile that work before altering shared models, repositories, or services.

The current owner has only a personal WeChat identity and has chosen to target a development build for now. The ICP-filed domain `tuitukj.com` is under the owner's DNS control, and `yoga.tuitukj.com` resolves to the intended public application server at `124.220.91.149`. A personal subject may be used to explore development tooling, but it is not accepted as the production basis for this commercial studio workflow because service-category approval, certification, member-card operations, and future payment capabilities may be unavailable. Production rollout therefore remains deferred behind explicit gates: register and verify an enterprise or individual-business subject, confirm an approved service category in the WeChat console, deploy FastAPI behind a valid TLS reverse proxy, configure PostgreSQL backup, and register the HTTPS API hostname in WeChat.

## Goals / Non-Goals

**Goals:**

- Add a native WeChat Mini Program for member and coach workflows.
- Bind a WeChat identity to an existing member or coach password account on first use.
- Reuse FastAPI JWT claims, RBAC, domain services, idempotency, and audit behavior.
- Keep Mini Program credentials and WeChat session material server-side.
- Give members and coaches mobile-specific navigation and task flows instead of translating desktop pages literally.
- Let members inspect their own card balance and validity without exposing administrator lifecycle operations.
- Let coaches manage their own private availability from the Mini Program.
- Give administrators an audited unbind action for account recovery.
- Preserve the Nuxt administrator application and its BFF cookie flow.

**Non-Goals:**

- Moving administrator operations into the Mini Program.
- Replacing the Nuxt frontend or Nitro BFF.
- Introducing WeChat Pay, subscription messages, phone-number login, social-profile synchronization, or non-WeChat clients.
- Replacing existing account opening, password reset, booking, writeoff, or private-training business rules.
- Automatically matching identities by nickname or phone number.
- Treating a personal Mini Program subject or development-tool domain bypass as production-ready.

## Decisions

### 1. Add a separate native WeChat client

Create a top-level `miniapp/` workspace using native WXML, WXSS, TypeScript, and WeChat project configuration. The client will have role-oriented pages and components but share only platform-neutral contracts and logic where extraction is demonstrably useful.

Native WeChat development is selected over Nuxt `web-view` because login, storage, navigation, review behavior, and future platform capabilities require a true Mini Program. It is selected over uni-app because the confirmed target is WeChat only; avoiding a cross-platform runtime reduces framework translation and platform-debugging risk. Nuxt Vue components are not treated as reusable Mini Program UI.

### 2. Call FastAPI directly from the Mini Program

The Mini Program calls an HTTPS FastAPI API domain configured as a WeChat request legal domain and sends `Authorization: Bearer <token>`. Existing business endpoints remain platform-neutral. Only WeChat authentication endpoints are platform-specific.

Routing Mini Program traffic through the current Nitro BFF was considered, but that layer primarily converts browser cookies into Bearer headers. Requiring it would add another runtime hop without benefiting the native client and would preserve browser-specific assumptions.

FastAPI CORS is not a Mini Program security boundary because `wx.request` is not a browser CORS flow. Authentication, authorization, TLS, WeChat domain registration, rate limiting, and backend validation remain mandatory.

### 3. Persist a separate WeChat identity mapping

Add a `wechat_identity` table associated with the existing account record rather than adding OpenID directly to member and coach tables. The record contains an internal ID, AppID, keyed OpenID digest, account ID, binding actor/time, and created/updated timestamps. Database constraints enforce unique `(appid, openid_digest)` and unique `(appid, account_id)` pairs.

This preserves the existing account as the authentication and role authority, avoids duplicating profile relationships, and leaves room for explicit unbinding or another WeChat application later. `unionid` is not required for the first release and must not be used as an implicit cross-application match.

The backend computes `HMAC-SHA-256(WECHAT_IDENTITY_PEPPER, appid + ":" + openid)` and stores only the digest because the first release does not need to recover raw OpenID. `WECHAT_IDENTITY_PEPPER` is a separate production secret from JWT and AppSecret. Raw OpenID and `session_key` exist only for the duration of code exchange and must never enter persistence, logs, traces, or client responses.

Add a `wechat_binding_challenge` table for unbound sessions with a random token digest, OpenID digest, AppID, expiry, consumed time, failed-attempt count, and request-source fingerprint. PostgreSQL is selected over Redis because the current deployment already requires PostgreSQL and the expected studio-scale binding volume does not justify another stateful dependency. Expired challenges are deleted by opportunistic cleanup and an operational maintenance job.

### 4. Use a two-step first binding protocol

The authentication flow is:

```text
Mini Program          FastAPI                 WeChat
    | wx.login code      |                       |
    |------------------->| code2Session          |
    |                    |---------------------->|
    |                    |<-- openid/session_key |
    |<-- binding ticket--|                       |
    | username/password  |                       |
    | + binding ticket   |                       |
    |------------------->| verify existing acct  |
    |<-- business JWT ---| bind atomically       |
```

An unbound exchange returns a cryptographically random opaque binding ticket whose digest is persisted in `wechat_binding_challenge`. It does not return OpenID or `session_key`. The binding endpoint locks and consumes the challenge, verifies credentials, rejects administrator accounts, reapplies current member/coach status rules, creates the mapping atomically, and issues the standard JWT. A challenge expires after a configurable short interval, permits a small configurable number of failed credential attempts, and cannot be replayed after success.

Returning users submit a new `wx.login` code; the server resolves the mapping, reloads the account and profile state, and issues a fresh standard JWT. The Mini Program never stores the account password after binding.

A one-step endpoint that accepts WeChat code and password together was considered. The two-step protocol gives a clear bound/unbound response and prevents account credentials from being resent on normal login while still requiring short ticket expiry, one-time consumption, and rate limits.

The concrete authentication API is:

- `POST /auth/wechat/session` with a one-time WeChat code, returning either `{ state: "bound", accessToken, role }` or `{ state: "binding_required", bindingTicket, expiresIn }`.
- `POST /auth/wechat/bind` with binding ticket, username, and password, returning the standard access token and role after atomic binding.
- Existing `GET /auth/me` remains the authoritative current-user response for both browser-derived and Mini Program Bearer tokens.

### 5. Keep existing JWT authorization semantics

Mini Program tokens use the existing signing algorithm and claims. Role, `memberId`, and `coachProfileId` are loaded from the account at issuance and validated by current FastAPI dependencies. The Mini Program stores the token using WeChat storage, attaches it only as a Bearer header, clears it on terminal authentication failure, and initiates `wx.login` again.

No client-provided member or coach identifier may select self-service resources. Server-side resource ownership checks remain authoritative. A separate refresh-token system is deferred; a bound user can recover a session through a new WeChat code when an access token expires.

### 6. Build role-specific mobile information architecture

After `/auth/me` confirms the role, the client enters one of two workspaces:

```text
Member                          Coach
├── Group schedule              ├── Assigned classes
├── Private training            ├── Attendance roster
├── My bookings                 ├── Private availability
├── My cards                    ├── Private requests
└── Account                     └── Account
```

Member schedules use chronological day groups rather than the Nuxt seven-column agenda. Coach entry pages prioritize assigned sessions and pending private-training work. Shared pages must still branch on server permissions, not merely hidden controls.

Existing class and private-training endpoints should be reused first. A new read-only aggregation endpoint is justified only if measurement shows that a page needs excessive sequential requests; it must not duplicate mutation logic.

Add `GET /members/me/cards` for member self-service. It derives `memberId` exclusively from the token and returns a dedicated read-only schema containing card product, type, status, remaining sessions, activation/expiry, and freeze dates. It does not reuse administrator response fields such as refundable transaction identifiers and does not expose mutation links.

Existing private-slot service ownership rules already support coaches. For native reliability, create, update, week generation, and cancellation accept an `Idempotency-Key`; endpoints introduced as non-idempotent browser APIs must accept the header optionally during migration so existing Nuxt callers do not break. Mini Program callers always send it, and replay persistence is applied when present.

### 7. Add explicit administrator recovery

Add a binding-status field or endpoint to the existing member/coach account administration views without exposing OpenID. Add `DELETE /accounts/{accountId}/wechat-binding` as an administrator-only operation with explicit confirmation and audit logging. The service locks the identity row, deletes the mapping, and records account ID, role, administrator, timestamp, and trace ID.

Direct transfer is deliberately excluded. After unbinding, the user runs the normal `wx.login` and credential-binding flow. Password reset from `improve-account-member-admin-flows` is the recovery path when the user no longer knows the original password.

### 8. Preserve idempotency across uncertain mobile networks

Each Mini Program mutation creates an idempotency key before submission, retains it while the outcome is uncertain, and reuses it for retries of the same payload. Keys are reset only after an authoritative response or an explicit user restart with changed input. Buttons are disabled during an in-flight operation, but backend idempotency remains the correctness boundary.

### 9. Separate public and private configuration

The AppID may be present in Mini Program project configuration. The AppSecret, identity pepper, and binding-ticket material exist only in backend environment or secret management and are never committed. Backend configuration must distinguish a fake provider used by automated tests, a development AppID used by developers, and production credentials, and must set explicit WeChat API timeouts.

The committed delivery target for this change is initially a development build. Code development starts with an injected fake code-exchange provider and local/test FastAPI, so lack of production credentials and a public server do not block domain logic or client page construction. Real `code2Session` integration requires a usable development AppID/AppSecret, and real-device legal-domain acceptance requires a public server. Production requires all of the following gates:

1. An enterprise or individual-business Mini Program subject suitable for the approved studio service category.
2. Completed platform verification and privacy declarations required by that category.
3. A public FastAPI deployment behind an ICP-compliant HTTPS hostname with a valid TLS chain.
4. The exact API hostname registered as a WeChat request legal domain.
5. Production AppSecret and identity pepper stored outside source control.

Development-tool domain bypass is allowed only for local debugging and is never acceptance evidence.

The production API hostname is `yoga.tuitukj.com`. Infrastructure verification on 2026-08-05 confirmed its A record resolves to `124.220.91.149` and HTTP reaches Nginx, while HTTPS currently fails during TLS negotiation and HTTP still serves the default Nginx page. Therefore DNS, ICP备案, and public-server provisioning are complete, but certificate issuance, HTTPS redirect, reverse proxy, FastAPI runtime and health check, PostgreSQL backup, and WeChat request-domain registration remain pending.

## Risks / Trade-offs

- [Concurrent account/auth changes cause migration or merge conflicts] -> Reconcile `improve-account-member-admin-flows` first and make the WeChat table reference the final account model.
- [OpenID or session material leaks through logs and traces] -> Redact provider payloads, never return raw identifiers, add log assertions, and audit only internal identity IDs or masked digests.
- [Stolen local token grants access until expiry] -> Keep access tokens short-lived, use HTTPS only, avoid URL/log exposure, and recheck account eligibility on every new WeChat login.
- [Credential binding enables username enumeration or brute force] -> Return uniform credential errors, rate-limit by binding identity and source, expire tickets quickly, and audit rejected attempts.
- [One account per AppID prevents intentional shared-device identities] -> Treat accounts as personal identities; resolve exceptional rebinding through a future audited administrator flow rather than weakening uniqueness.
- [Direct API calls expose a broader endpoint surface] -> Rely on backend RBAC and ownership checks, verify every Mini Program endpoint with role-bound integration tests, and never depend on hidden client controls.
- [Native client duplicates frontend presentation code] -> Share only stable TypeScript contracts and pure logic; accept separate UI code as the cost of native behavior.
- [Mobile network interruption creates ambiguous mutations] -> Persist operation keys through retries and refresh authoritative resources after mutation responses.
- [WeChat API or review policy changes] -> Isolate provider calls behind a service interface and verify current platform requirements before production submission.
- [Personal subject cannot pass the required commercial service-category review] -> Make non-personal subject registration and console category confirmation a release gate before full production investment.
- [The public hostname exists but is mistaken for a production-ready API] -> Keep production blocked until `yoga.tuitukj.com` has valid TLS, redirects HTTP to HTTPS, proxies to FastAPI, exposes a passing health check, and has PostgreSQL backup and monitoring in place.

## Migration Plan

1. Complete and verify `improve-account-member-admin-flows`, especially password reset and disabled-member recovery, then freeze the account relationship used by the identity foreign key.
2. Verify the current private-training/reporting implementation and migration `0007`; allocate the next migration revision only after that baseline is stable.
3. Treat confirmed ownership, ICP备案, DNS for `yoga.tuitukj.com`, and its public server as the infrastructure baseline; retain TLS, reverse proxy, FastAPI deployment, PostgreSQL backup, and non-personal subject registration as deferred production prerequisites rather than blockers for the development build.
4. Add binding challenge and identity migrations, fake provider integration, authentication services, administrator unbinding, member-self cards, availability idempotency, and backend tests without changing browser authentication behavior.
5. Create the native Mini Program workspace and implement authentication plus role routing against the fake/test environment.
6. Add member flows, including read-only cards, then coach flows, including private availability, validating each mutation against existing domain services.
7. Stop the current development milestone after fake-provider authentication, local/test backend integration, automated tests, and WeChat Developer Tools acceptance are complete.
8. In a later production milestone, complete FastAPI HTTPS hosting on `yoga.tuitukj.com`, register a non-personal subject and the request domain, integrate real `code2Session`, complete physical-device acceptance, and only then consider trial release and review submission.

Rollback disables the Mini Program authentication endpoints or credentials and withdraws the Mini Program release. Existing Nuxt and FastAPI browser flows continue unchanged. The identity table can remain dormant; destructive rollback is unnecessary.

## Open Questions

- Which enterprise or individual-business entity will own a future production Mini Program, and which service category will its WeChat management console permit for this studio?
- Which deployment secret-management facility will hold AppSecret, `WECHAT_IDENTITY_PEPPER`, and JWT secret?
- What access-token and binding-challenge lifetimes will be selected after security testing of the first integrated build?
