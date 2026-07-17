# Tasks: member-card-core（会员与卡项核心）

**Input**: Design documents from `/specs/002-member-card-core/`
**Prerequisites**: `plan.md` (required), `spec.md` (required), `research.md`, `data-model.md`, `contracts/member-card-core.openapi.yaml`, `quickstart.md`

**Tests**: Every user story includes executable acceptance tests for Normal/Boundary/Exception flows and traceability mapping to spec/PRD IDs.

**Organization**: Tasks are grouped by user story so each story can be implemented and tested independently.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Initialize frontend/backend workspaces and baseline toolchain.

- [X] T001 Create backend project skeleton and dependency groups in `backend/pyproject.toml`
- [X] T002 Create frontend Nuxt workspace and baseline config in `frontend/nuxt.config.ts`
- [X] T003 [P] Add local dev environment template for API/DB settings in `backend/.env.example`
- [X] T004 [P] Add backend test runner configuration for pytest markers and coverage in `backend/pytest.ini`
- [X] T005 [P] Add frontend test runner configuration for unit/e2e in `frontend/package.json`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core capabilities required by all user stories.

**CRITICAL**: No user story work starts before this phase completes.

- [X] T006 Implement SQLAlchemy engine/session and unit-of-work bootstrap in `backend/app/infra/db/session.py`
- [X] T007 Create Alembic base migration for shared enums/extensions in `backend/alembic/versions/0001_base_foundation.py`
- [X] T008 [P] Implement request context + trace ID middleware in `backend/app/api/middleware/request_context.py`
- [X] T009 [P] Implement JWT auth dependency and role guard helpers in `backend/app/api/deps/auth.py`
- [X] T010 [P] Implement RBAC/ownership policy service for admin/coach/member in `backend/app/services/access_policy_service.py`
- [X] T011 Implement append-only audit logging service and repository in `backend/app/services/audit_log_service.py`
- [X] T012 Implement idempotency key persistence and replay service in `backend/app/services/idempotency_service.py`
- [X] T013 [P] Wire FastAPI router registry and global error handling in `backend/app/api/main.py`
- [X] T014 [P] Create generated API client wrapper for Nuxt BFF calls in `frontend/composables/useApiClient.ts`
- [X] T015 Add OpenAPI contract validation test harness against backend app in `backend/tests/contract/test_openapi_contract.py`

**Checkpoint**: Foundation ready. User stories can be implemented independently.

---

## Phase 3: User Story 1 - 管理员维护会员与卡项基础资料 (Priority: P1) 🎯 MVP

**Goal**: 管理员可完成会员资料和卡项模板的新增/编辑/查询/软删除/状态管理，并阻止越权。

**Independent Test**: 仅部署 US1 代码即可完成 US1-AS1/AS2/AS3/AS4，且教练越权写操作被拒绝并留痕。

### Tests for User Story 1 (MANDATORY)

- [X] T016 [P] [US1] Add normal-flow acceptance tests for member/card-product create and query in `backend/tests/integration/test_us1_normal_member_cardproduct.py`
- [X] T017 [P] [US1] Add boundary-flow acceptance tests for disabled member booking guard in `backend/tests/integration/test_us1_boundary_member_status.py`
- [X] T018 [P] [US1] Add exception-flow acceptance tests for coach unauthorized write attempts in `backend/tests/integration/test_us1_exception_rbac.py`
- [X] T019 [US1] Map US1 tests to spec acceptance and PRD rows in `specs/002-member-card-core/checklists/acceptance-traceability.md`

### Implementation for User Story 1

- [X] T020 [P] [US1] Implement Member ORM model with soft-delete/status fields in `backend/app/domain/member.py`
- [X] T021 [P] [US1] Implement CardProduct ORM model with core rule fields in `backend/app/domain/card_product.py`
- [X] T022 [US1] Implement member repository methods for CRUD and status transition in `backend/app/repositories/member.py`
- [X] T023 [US1] Implement card product repository methods for template management in `backend/app/repositories/card_product.py`
- [X] T024 [US1] Implement member application service with ownership and soft-delete rules in `backend/app/services/member.py`
- [X] T025 [US1] Implement card product application service with field validation rules in `backend/app/services/card_product.py`
- [X] T026 [US1] Implement members API endpoints (`POST/PATCH/DELETE /members/{id}`) in `backend/app/api/endpoints/members.py`
- [X] T027 [US1] Implement card-products API endpoint (`POST /card-products`) in `backend/app/api/endpoints/card_products.py`
- [X] T028 [P] [US1] Build Nuxt member list/form page with admin-only actions in `frontend/pages/members.vue`
- [X] T029 [P] [US1] Build Nuxt card product creation page with rule fields in `frontend/pages/cards.vue`
- [X] T030 [US1] Add frontend route middleware checks for US1 admin pages in `frontend/middleware/require-admin.ts`

**Checkpoint**: User Story 1 is independently functional and testable (MVP).

---

#


# Phase 4: User Story 2 - 管理员办理卡项交易与状态变更 (Priority: P2)

**Goal**: 管理员可完成购卡/续费/补卡/退款、冻结/解冻/延期、过期提醒，并保证幂等与并发安全。

**Independent Test**: 仅部署 US2 增量即可完成 US2-AS1/AS2/AS3/AS4，重复退款请求不重复生效。

### Tests for User Story 2 (MANDATORY)

- [X] T031 [P] [US2] Add normal-flow acceptance tests for purchase/renew/freeze/unfreeze lifecycle in `backend/tests/integration/test_us2_normal_transactions.py`
- [X] T032 [P] [US2] Add boundary-flow acceptance tests for expiry reminder and freeze extension logic in `backend/tests/integration/test_us2_boundary_expiry_freeze.py`
- [X] T033 [P] [US2] Add exception-flow acceptance tests for idempotent refund replay in `backend/tests/integration/test_us2_exception_idempotent_refund.py`
- [X] T034 [US2] Map US2 tests to spec acceptance and PRD rows in `specs/002-member-card-core/checklists/acceptance-traceability.md`

### Implementation for User Story 2

- [X] T035 [P] [US2] Implement MemberCard ORM model with freeze/expiry/reminder fields in `backend/app/domain/member_card.py`
- [X] T036 [P] [US2] Implement CardTransaction ORM model with idempotency and trace fields in `backend/app/domain/card_transaction.py`
- [X] T037 [US2] Implement member card repository with FEFO candidate queries and row locks in `backend/app/repositories/member_card_repository.py`
- [X] T038 [US2] Implement transaction repository with unique idempotency persistence in `backend/app/repositories/transaction_repository.py`
- [X] T039 [US2] Implement transaction service for purchase/renew/reissue/refund flows in `backend/app/services/transaction_service.py`
- [X] T040 [US2] Implement card lifecycle service for freeze/unfreeze/extend/reminder calculation in `backend/app/services/member_card_lifecycle_service.py`
- [X] T041 [US2] Implement transactions API endpoint (`POST /transactions`) with idempotency handling in `backend/app/api/endpoints/transactions.py`
- [X] T042 [US2] Implement member-card lifecycle endpoints (`POST /member-cards/{id}/freeze|unfreeze`) in `backend/app/api/endpoints/member_cards.py`
- [X] T043 [P] [US2] Build Nuxt transaction operation page for purchase/renew/refund actions in `frontend/pages/transactions/index.vue`
- [X] T044 [P] [US2] Build Nuxt member-card lifecycle controls for freeze/unfreeze/expiry badges in `frontend/components/member-cards/MemberCardLifecyclePanel.vue`
- [X] T045 [US2] Add duplicate-submit protection and idempotency-key generation in `frontend/composables/useIdempotentSubmit.ts`

**Checkpoint**: User Stories 1 and 2 both work independently.

---

## Phase 5: User Story 3 - 运营人员查询会员业务记录并核对核销链路 (Priority: P3)

**Goal**: 管理员/授权运营可按会员时间线查询记录并核对核销链路，会员越权查询被拒绝且留痕。

**Independent Test**: 仅部署 US3 增量即可完成 US3-AS1/AS2/AS3/AS4，时间线可复盘预扣/实扣/返还关系。

### Tests for User Story 3 (MANDATORY)

- [X] T046 [P] [US3] Add normal-flow acceptance tests for member timeline queries and write-off linkage in `backend/tests/integration/test_us3_normal_timeline.py`
- [X] T047 [P] [US3] Add boundary-flow acceptance tests for same-day multi-event ordering in `backend/tests/integration/test_us3_boundary_timeline_order.py`
- [X] T048 [P] [US3] Add exception-flow acceptance tests for cross-member read denial in `backend/tests/integration/test_us3_exception_cross_member_access.py`
- [X] T049 [US3] Map US3 tests to spec acceptance and PRD rows in `specs/002-member-card-core/checklists/acceptance-traceability.md`

### Implementation for User Story 3

- [X] T050 [P] [US3] Implement WriteOffEvent ORM model with lifecycle sequencing fields in `backend/app/domain/writeoff_event.py`
- [X] T051 [P] [US3] Implement timeline projection query model for mixed event stream in `backend/app/domain/member_timeline_view.py`
- [X] T052 [US3] Implement write-off repository with lifecycle transition validation in `backend/app/repositories/writeoff_repository.py`
- [X] T053 [US3] Implement write-off service for `reserve_hold -> checkin_commit -> cancel_refund` chain in `backend/app/services/writeoff_service.py`
- [X] T054 [US3] Implement timeline query service aggregating transaction/write-off/audit logs in `backend/app/services/member_timeline_service.py`
- [X] T055 [US3] Implement write-off events API endpoint (`POST /writeoff/events`) in `backend/app/api/routes/writeoff.py`
- [X] T056 [US3] Implement member timeline API endpoint (`GET /members/{id}/timeline`) with role scoping in `backend/app/api/routes/timeline.py`
- [X] T057 [P] [US3] Build Nuxt member timeline page with filters and chronological stream in `frontend/pages/members/[memberId]/timeline.vue`
- [X] T058 [P] [US3] Build write-off chain detail drawer component for pre-deduct/commit/refund links in `frontend/components/timeline/WriteoffChainDrawer.vue`

**Checkpoint**: All user stories are independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Hardening, documentation, and end-to-end verification across stories.

- [X] T059 [P] Add structured logging and OpenTelemetry enrichment for key business spans in `backend/app/infra/observability.py`
- [X] T060 [P] Add PostgreSQL performance indexes and constraint tuning migration in `backend/alembic/versions/0005_perf_indexes.py`
- [X] T061 Update quickstart runbook with final API/UI validation evidence in `specs/002-member-card-core/quickstart.md`
- [X] T062 Run full acceptance suite and capture execution report in `specs/002-member-card-core/checklists/acceptance-report.md`
- [X] T063 [P] Add frontend UX polish for loading/empty/error states across member-card pages in `frontend/components/common/AsyncState.vue`

---

## Dependencies & Execution Order

### Phase Dependencies

- Setup (Phase 1) has no prerequisites.
- Foundational (Phase 2) depends on Setup and blocks all story implementation.
- User stories (Phases 3-5) depend on Foundational completion.
- Polish (Phase 6) depends on completion of selected stories.

### User Story Dependency Graph

- `US1 (P1)` -> enables baseline master data for all later operations.
- `US2 (P2)` -> depends on US1 entities (member/card product) but remains independently testable once baseline data exists.
- `US3 (P3)` -> depends on US2 write-off/transaction events for full timeline richness; still independently testable with seeded fixtures.

Graph: `US1 -> US2 -> US3`

### Within Each User Story

- Write acceptance tests first and verify failing state.
- Implement domain/repository before service orchestration.
- Implement API endpoints after service logic.
- Implement frontend integration after API contracts are green.

### Parallel Opportunities

- Setup: T003/T004/T005 can run in parallel after T001/T002.
- Foundational: T008/T009/T010/T013/T014 can run in parallel after T006.
- US1: T016/T017/T018 parallel; T020/T021 parallel; T028/T029 parallel.
- US2: T031/T032/T033 parallel; T035/T036 parallel; T043/T044 parallel.
- US3: T046/T047/T048 parallel; T050/T051 parallel; T057/T058 parallel.
- Polish: T059/T060/T063 parallel.

---

## Parallel Example: User Story 1

```bash
# Acceptance tests in parallel
pytest backend/tests/integration/test_us1_normal_member_cardproduct.py
pytest backend/tests/integration/test_us1_boundary_member_status.py
pytest backend/tests/integration/test_us1_exception_rbac.py

# UI work in parallel
pnpm --dir frontend test -- members
pnpm --dir frontend test -- card-products
```

## Parallel Example: User Story 2

```bash
# Transaction lifecycle tests in parallel
pytest backend/tests/integration/test_us2_normal_transactions.py
pytest backend/tests/integration/test_us2_boundary_expiry_freeze.py
pytest backend/tests/integration/test_us2_exception_idempotent_refund.py

# Feature UI tasks in parallel
pnpm --dir frontend test -- transactions
pnpm --dir frontend test -- member-cards
```

## Parallel Example: User Story 3

```bash
# Timeline and authorization tests in parallel
pytest backend/tests/integration/test_us3_normal_timeline.py
pytest backend/tests/integration/test_us3_boundary_timeline_order.py
pytest backend/tests/integration/test_us3_exception_cross_member_access.py

# Timeline UI tasks in parallel
pnpm --dir frontend test -- timeline
pnpm --dir frontend test -- writeoff-chain
```

---

## Implementation Strategy

### MVP First (US1 only)

1. Complete Phase 1 and Phase 2.
2. Complete Phase 3 (US1) and run US1 acceptance tests.
3. Demo/deploy MVP for member and card-product master data management.

### Incremental Delivery

1. Deliver US1 (master data + RBAC baseline).
2. Deliver US2 (transactions + lifecycle + idempotency hardening).
3. Deliver US3 (timeline + write-off chain auditability).
4. Run Phase 6 polish and full acceptance report.

### Parallel Team Strategy

1. Team aligns on Phase 1-2 foundation.
2. After foundation: backend/frontend pairs split per story phase.
3. Merge by contract boundaries and acceptance checkpoints per story.

---

## Notes

- All tasks use checklist format: `- [X] Txxx [P] [USx] Description with file path`.
- `[USx]` labels are applied only to user-story tasks.
- Each story has explicit independent test criteria and acceptance traceability updates.
