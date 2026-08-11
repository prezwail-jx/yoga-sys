# Administrator Binding Recovery Acceptance

Date: 2026-08-06

## Implemented

- Administrators can query `GET /accounts/{accountId}/wechat-binding` for member and coach accounts. The response contains only account ID, bound state, and binding time.
- `DELETE /accounts/{accountId}/wechat-binding` requires `{ "confirm": true }`, serializes through the existing account advisory lock and identity row lock, and returns `409 wechat_binding_not_found` for an unbound account.
- Successful unbind records the administrator, affected account, role, trace ID, and `wechatBound: false`; it never records OpenID or its digest.
- A non-administrator receives 403, the binding remains intact, and the existing rejection middleware writes the rejected privileged-operation audit.
- WeChat session lookup now locks a bound identity while constructing a JWT, preventing a concurrent unbind from interleaving with new-token issuance.
- Member and coach administration screens show binding state and require an explicit second confirmation before unbinding. No direct transfer action is exposed.

## Verification

| Check | Result |
| --- | --- |
| PostgreSQL recovery integration and OpenAPI tests | Passed: 8 tests |
| Full backend suite | Passed: 1 existing skip, 86% coverage |
| `npm run typecheck` | Passed |
| `npm run test:unit` | Passed: 9 files, 23 tests |
| `openspec validate add-wechat-mini-program` | Passed |
| `git diff --check` | Passed |
