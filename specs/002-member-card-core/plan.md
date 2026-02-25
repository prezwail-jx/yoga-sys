# Implementation Plan: member-card-core（会员与卡项核心）

**Branch**: `002-member-card-core` | **Date**: 2026-02-25 | **Spec**: `/home/paul/workspace/yoga-sys/specs/002-member-card-core/spec.md`
**Input**: Feature specification from `/home/paul/workspace/yoga-sys/specs/002-member-card-core/spec.md` and user constraints (Vue+Nuxt admin based on dashboard-vue, Python 3 backend, uv venv in `backend/`, PostgreSQL 16.11, no Redis in this phase)

## Summary

本 feature 采用前后端分离 Web 应用结构：前端使用 Vue 3 + Nuxt 3（UI 参考 `nuxt-ui-templates/dashboard-vue`），后端使用 Python 3 + FastAPI + SQLAlchemy 2 + PostgreSQL 16.11，并以 `uv` 在 `backend/` 创建虚拟环境。本阶段不引入 Redis，幂等与并发一致性由 PostgreSQL 事务、唯一约束与行级锁保障。

## Technical Context

**Language/Version**: Python 3.12（backend）, TypeScript 5.x + Vue 3 + Nuxt 3（frontend）  
**Primary Dependencies**: FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic, PostgreSQL 16.11, structlog, OpenTelemetry, Nuxt UI  
**Storage**: PostgreSQL 16.11  
**Testing**: pytest, pytest-cov, httpx, testcontainers (PostgreSQL), schemathesis; frontend 使用 Vitest + Playwright  
**Target Platform**: Linux server（API/Nuxt SSR），现代桌面与移动浏览器（admin）
**Project Type**: Web application（frontend + backend）  
**Performance Goals**: 关键写接口 p95 < 300ms；会员时间线查询 p95 < 500ms（50 条/页）  
**Constraints**: 必须满足宪章五项原则；所有关键写操作强制幂等；软删除不可破坏历史链路；本阶段不引入 Redis  
**Scale/Scope**: 1k-20k 会员；日均交易与核销事件 5k；管理员/教练/会员三角色

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **P1 Role & Permission Isolation**: PASS。后端 API 统一执行 JWT 鉴权 + RBAC（管理员/教练/会员）+ 资源归属校验；前端仅作体验层路由守卫。
- **P2 Card Write-off Consistency**: PASS。合同与数据模型统一 `预约预扣 -> 签到实扣 -> 取消返还`，并记录命中规则、操作人、trace id。
- **P3 Concurrency & Idempotency**: PASS。交易/核销/冻结解冻使用事务边界 + `Idempotency-Key` + 唯一索引 + 行级锁策略（仅 PostgreSQL，无 Redis 依赖）。
- **P4 Observability & Traceability**: PASS。审计日志覆盖购卡/续费/退款/预约/取消/签到/核销/冻结/解冻，支持按会员时间线检索。
- **P5 Acceptance-First**: PASS。需求与验收场景已在 `spec.md` 完整映射 PRD，且包含正常/边界/异常流。

## Project Structure

### Documentation (this feature)

```text
specs/002-member-card-core/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
└── tasks.md
```

### Source Code (repository root)

```text
backend/
├── pyproject.toml
├── uv.lock
├── .venv/
├── alembic.ini
├── alembic/
├── app/
│   ├── api/
│   ├── domain/
│   ├── services/
│   ├── repositories/
│   ├── schemas/
│   └── infra/
└── tests/
    ├── unit/
    ├── integration/
    └── contract/

frontend/
├── nuxt.config.ts
├── app.vue
├── pages/
├── components/
├── middleware/
├── composables/
├── server/api/
└── tests/
    ├── unit/
    └── e2e/
```

**Structure Decision**: 采用 Web application 双目录结构（`frontend/` + `backend/`），以 Nuxt 承载后台管理界面和 BFF 代理能力，以 FastAPI 承载领域 API 与审计能力。

## Post-Design Constitution Re-check

- **P1**: PASS（contracts 已为敏感接口设置鉴权前提，且会员时间线查询带角色边界）
- **P2**: PASS（write-off 合同与实体生命周期一致）
- **P3**: PASS（data-model 定义幂等键和唯一约束）
- **P4**: PASS（审计实体与 quickstart 覆盖追溯核查路径）
- **P5**: PASS（quickstart 场景逐项映射 spec 验收条目）

## Complexity Tracking

无宪章违规项，无需豁免。
