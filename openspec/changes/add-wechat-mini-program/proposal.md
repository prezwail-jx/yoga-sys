## Why

The system currently serves members and coaches through the same Nuxt operations interface used by administrators, which limits mobile usability and provides no native WeChat login or mini-program experience. A dedicated WeChat Mini Program can expose the existing booking workflows where members and coaches already work while preserving the Nuxt administrator console and FastAPI business rules.

## What Changes

- Add a native WeChat Mini Program client for member and coach roles.
- Add WeChat login and first-use binding to an existing username/password account without exposing the WeChat AppSecret to clients.
- Add an audited administrator unbind action so an incorrectly bound account or a user changing WeChat identity can recover without direct database changes.
- Issue the existing role-bound JWT claims after a WeChat identity is bound, and continue enforcing member and coach resource isolation in FastAPI.
- Add member flows for class schedules, class booking and cancellation, private-training booking and cancellation, personal booking history, and read-only card balance/status visibility.
- Add coach flows for assigned class schedules, class attendance work, private availability publishing and cancellation, private-training decisions, and lesson sign-in records.
- Keep the Nuxt administrator console and its cookie-based BFF authentication unchanged.
- Establish HTTPS domain, configuration, automated test, and release requirements for the Mini Program.
- Make completion of `improve-account-member-admin-flows` a prerequisite so password recovery and account-status behavior are stable before WeChat binding is introduced.
- Treat a verified non-personal Mini Program subject and an ICP-compliant HTTPS API domain as production-release gates. Development may proceed with provider mocks and a development AppID, but the current personal-only subject MUST NOT be treated as sufficient for commercial release.
- Set the current delivery target to a development build using a fake WeChat provider and local/test backend. The owner has an ICP-filed domain and a public server, but production TLS, reverse proxy, FastAPI deployment, backup, and a non-personal production subject are not ready, so real-device production authentication and review submission remain deferred.
- Exclude administrator operations, WeChat Pay, subscription messages, and non-WeChat application platforms from the initial release.

## Capabilities

### New Capabilities

- `wechat-mini-program-auth`: WeChat code exchange, existing-account binding, repeat login, token issuance, disabled-account handling, identity isolation, and audited administrator unbinding.
- `member-mini-program`: Native member schedule, group-class booking, private-training booking, cancellation, personal booking, and read-only member-card views.
- `coach-mini-program`: Native coach schedule, attendance, private availability management, private-training decision, and lesson completion workflows.

### Modified Capabilities

None. Existing account-opening, class-booking, and private-training requirements remain authoritative and are consumed by the new client.

## Impact

- Backend: WeChat identity persistence, server-side WeChat API integration, authentication endpoints, audit events, configuration, and tests.
- Client: a new native WeChat Mini Program workspace, role-based navigation, API client, token lifecycle, and end-to-end interaction tests.
- Existing frontend: no platform conversion; Nuxt remains the administrator-facing web application and BFF, with a small administrator control added for audited WeChat unbinding.
- Existing APIs: add a member-self card query and idempotent Mini Program support for coach availability mutations while preserving current administrator and browser clients.
- Infrastructure: ownership, DNS control, ICP备案, and the public server have been confirmed for `yoga.tuitukj.com` (`124.220.91.149`). Production release remains blocked until valid TLS, reverse proxy, FastAPI deployment and health checks, PostgreSQL backup, a suitable enterprise or individual-business subject, approved service category, registered Mini Program request domain, protected AppID/AppSecret configuration, and privacy/release configuration are available.
- Delivery coordination: `improve-account-member-admin-flows` must be implemented and verified before this change modifies shared account or authentication files; the current private-training/reporting work must pass its existing acceptance checks before Mini Program client integration begins.
