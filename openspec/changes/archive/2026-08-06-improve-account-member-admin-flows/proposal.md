## Why

During private-training and member-account manual verification, several administrator workflow gaps became visible: administrators cannot reset member or coach passwords, disabled members cannot be re-enabled, duplicate username errors are easy to misunderstand, and private-training failures can still surface as generic server errors without enough user guidance.

These gaps do not block the current private-training/reporting implementation, but they affect day-to-day operations and should be tracked as a first-class OpenSpec change rather than only as notes.

## What Changes

- Add administrator password reset capability for member and coach accounts without exposing existing passwords or password hashes.
- Allow administrators to re-enable disabled members while preserving historical account, card, transaction, writeoff, and audit data.
- Improve account-opening UX around globally unique usernames and already-bound accounts.
- Improve private-training error handling and test coverage so common failures return actionable messages instead of generic `Internal Server Error`.

> [!IMPORTANT]
> **🔐 会员自助修改密码** — 已登录会员可在前端自主修改自己的密码，需验证旧密码。与管理员重置密码并存，互不冲突。

> [!IMPORTANT]
> **👁️ 管理员查看会员账号状态** — 会员列表中醒目展示哪些会员已开通账号/未开通，管理员一眼可辨，便于业务管理。

## Capabilities

### Modified Capabilities

- `member-account-binding`: Password reset, duplicate username messaging, disabled-member re-enable flow, and account-management tests.

### New Capabilities

- `private-training-error-handling`: Private-training endpoint and frontend error-message hardening for create/book/confirm/reject/cancel/sign-in flows.

## Impact

- Backend: account reset endpoint(s), member status transition adjustment, audit logging, and additional tests.
- Frontend: member/coach account reset actions, disabled-member re-enable button, clearer duplicate username guidance, and private-training error presentation.
- Security: passwords remain non-readable; reset operations are admin-only and audited.
- Product docs: `spec/feats/003-follow-up-account-member-admin-20260730.md` remains the discovery note linked to this change.
