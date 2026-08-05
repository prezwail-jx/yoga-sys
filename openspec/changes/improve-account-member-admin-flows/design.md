## Context

The system already supports administrator-created member and coach accounts, JWT-bound member/coach identities, member status transitions, role-based guards, and append-only audit logs. Current gaps are operational rather than architectural.

The existing account-binding design intentionally does not expose plaintext passwords. That principle must remain unchanged; forgotten credentials should be handled by reset, not by password lookup.

## Goals / Non-Goals

**Goals:**

- Let administrators reset passwords for existing member and coach accounts.
- Let administrators restore disabled members to `normal` when needed.
- Make username uniqueness and already-bound account states clearer in the UI.
- Ensure private-training workflows produce actionable errors for expected business failures.

**Non-Goals:**

- Do not show or recover original passwords.
- Do not add SMS, email, or WeChat verification in this change.
- Do not change member card balances or historical records during re-enable.
- Do not build a full account administration console unless required by implementation.

## Decisions

### Decision: Reset Passwords Instead Of Viewing Passwords

Administrators may set a new temporary password for a member or coach account. The backend stores only a new secure hash and returns no password hash.

Rationale: Password visibility is a security anti-pattern. Reset is operationally sufficient and auditable.

### Decision: Make Disabled Member Re-enable Explicit

Allow `disabled -> normal` only through administrator update paths and show a dedicated “重新启用” action in member management.

Rationale: Operators need to correct accidental disables or reactivate returning members without losing business history.

### Decision: Keep Username Errors Safe But Clear

The backend can keep returning 409 for duplicate usernames. The frontend should explain that usernames are globally unique and recommend choosing another username.

Rationale: This improves admin understanding without leaking unnecessary account ownership details to clients.

### Decision: Harden Private-Training Error Surfaces

Expected conflicts and validation failures should use explicit `HTTPException` responses. The frontend should map 401/403/409/422/500 into useful Chinese messages and keep trace IDs available for unexpected failures.

Rationale: Operators should not see unexplained server errors for common business cases.

### Decision: Member Self-Service Password Change

Logged-in members can change their own password via `POST /auth/change-password` providing old password and new password. The backend validates the old password before overwriting the hash. No admin involvement needed.

Rationale: Members should control their own credentials without asking an admin every time. Old-password verification prevents unauthorized changes on shared devices.

### Decision: Account Status Column In Member List

The member list response (`GET /members`) includes `has_account: bool` and `username: str | null`, derived from the `AdminUser` member-binding. The admin frontend displays a prominent badge/tag per row: 🔵 "已开通" or ⚪ "未开通", with the username visible on hover or inline.

Rationale: Administrators need at-a-glance visibility of account binding status for day-to-day operations without clicking into each member detail.

## Risks / Trade-offs

- Password reset can be abused if administrator credentials are compromised -> keep admin-only guard and audit every reset.
- Re-enabling disabled members may restore booking eligibility immediately -> require explicit admin action and preserve audit history.
- More specific username errors may reveal existence -> keep messages generic enough for security while clearer for operators.
- Private-training generic 500s may still happen for unknown bugs -> ensure trace ID is visible and tests cover known flows.

## Implementation Notes

- Reuse existing `AdminUserRepository` and password hashing utilities for reset.
- Reuse existing member update endpoint for `disabled -> normal` unless an explicit state-transition endpoint is cleaner.
- Add tests for admin-only access, old password invalidation, new password login, and audit creation.
- Add tests or smoke coverage for private-training create slot, booking request, confirm, reject, cancel, and sign-in error paths.
