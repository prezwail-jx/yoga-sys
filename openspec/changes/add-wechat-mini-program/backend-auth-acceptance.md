# Backend WeChat Authentication Acceptance

Date: 2026-08-06

## Implemented

- `POST /auth/wechat/session` exchanges a code server-side and returns either a standard JWT for a bound, eligible account or a short-lived binding ticket.
- `POST /auth/wechat/bind` locks and consumes challenges, commits failed credential counters through normal error responses, rejects administrators and ineligible accounts, and uses the existing database uniqueness boundary for binding conflicts.
- Password and WeChat authentication both issue tokens through `AuthService.issue_token_for_account`, so member and coach claims are built from the current account and profile records.
- Binding attempts are limited by challenge attempts and a process-local source fingerprint sliding window. Production deployment must retain the corresponding reverse-proxy limit because application memory is not shared across workers.
- Audit events use the `system` actor and never include password, JWT, raw ticket, OpenID, AppSecret, or `session_key` values.

## Verification

| Check | Result |
| --- | --- |
| `TEST_DATABASE_URL=... uv run pytest -q` | Passed: full backend suite, 1 existing skip, 85% coverage |
| WeChat auth and persistence PostgreSQL integration tests | Passed: 20 tests |
| OpenAPI WeChat auth contract tests | Passed: 4 tests |
| `uv run python -m compileall -q app` | Passed |
| `npm run typecheck` | Passed |
| `npm run test:unit` | Passed: 9 files, 22 tests |
| `openspec validate add-wechat-mini-program` | Passed |

## Scope Note

The default test-container PostgreSQL path timed out on this host after container startup. The dedicated local test database configured by `TEST_DATABASE_URL` completed the full backend suite successfully.
