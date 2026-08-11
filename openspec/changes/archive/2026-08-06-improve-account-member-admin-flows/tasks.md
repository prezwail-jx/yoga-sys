## 1. Password Reset

- [x] 1.1 Add backend service method and route for administrator reset of member account passwords.
- [x] 1.2 Add backend service method and route for administrator reset of coach account passwords.
- [x] 1.3 Ensure reset stores only a new password hash and never returns plaintext after the request is processed.
- [x] 1.4 Record audit logs for password reset actions without storing plaintext passwords.
- [x] 1.5 Add backend tests for admin-only reset, old password invalidation, new password login, missing account, and audit coverage.

## 1b. Member Self-Service Password Change ⭐

- [x] 1b.1 Add `POST /auth/change-password` endpoint accepting old password + new password.
- [x] 1b.2 Validate old password before overwriting hash; return 401 on mismatch.
- [x] 1b.3 Restrict to `role=member`; return 403 for admin/coach via this endpoint.
- [x] 1b.4 Add backend tests for correct old password, wrong old password, non-member access, and post-reset flow.
- [x] 1b.5 Add frontend password-change form in member self-service area, validate new password strength.

## 2. Disabled Member Re-enable

- [x] 2.1 Update member status transition rules to allow administrator-driven `disabled -> normal`.
- [x] 2.2 Add member-management UI action for disabled members to "重新启用".
- [x] 2.3 Ensure re-enabled members keep existing accounts, cards, transactions, writeoff events, and audit history.
- [x] 2.4 Add backend and frontend tests for disabled-member re-enable.

## 3. Account Opening UX

- [x] 3.1 Update member and coach account-opening forms to state that usernames are globally unique.
- [x] 3.2 Improve duplicate username error display with a clear Chinese message.
- [x] 3.3 Keep already-bound member/coach buttons disabled with explicit "账号已开通" state.
- [x] 3.4 Add frontend tests for duplicate username and already-bound account states.

## 3b. Admin Member List - Account Status Column ⭐

- [x] 3b.1 Extend `GET /members` response with `has_account: bool` and `username: str | None`.
- [x] 3b.2 Display prominent badge/tag per member row: "已开通" (blue) or "未开通" (gray).
- [x] 3b.3 Show username inline or on hover for bound members.
- [x] 3b.4 Add "重置密码" action button for bound members; "开通账号" for unbound.
- [x] 3b.5 Add frontend unit/E2E tests for account status column rendering and action buttons.

## 4. Private-Training Error Handling

- [x] 4.1 Audit private-training service methods for expected conflicts/validation failures and convert them to explicit HTTP errors where missing.
- [x] 4.2 Improve frontend private-training error messages for 401, 403, 409, 422, and unexpected 500 responses.
- [x] 4.3 Add backend smoke or integration tests for private slot create/list, booking create/list, confirm, reject, cancel, and sign-in.
- [x] 4.4 Add E2E coverage for private slot creation and error display.

## 5. Verification And Docs

- [x] 5.1 Run backend unit and contract checks.
- [x] 5.2 Run frontend lint, typecheck, unit tests, and relevant E2E tests.
- [x] 5.3 Update `features.md` and related docs after implementation.
