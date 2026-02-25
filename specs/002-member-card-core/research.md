# Phase 0 Research: member-card-core

## Decision 1: Frontend baseline（Vue + Nuxt）

- Decision: 管理后台采用 Vue 3 + Nuxt 3 + Nuxt UI，布局与交互参考 `nuxt-ui-templates/dashboard-vue`。
- Rationale: 兼顾后台模板成熟信息架构与 Nuxt 的路由中间件、SSR/BFF 能力，适合 RBAC 管理端。
- Alternatives considered:
  - 直接使用 dashboard-vue(Vite) 作为主架构：上手快，但缺少 Nuxt server routes 与统一 BFF 能力。
  - 纯 Vue SPA：工程更轻，但在鉴权、代理、SSR 场景扩展性较弱。

## Decision 2: Backend framework（Python + PostgreSQL）

- Decision: 后端采用 Python 3.12 + FastAPI + Pydantic v2 + SQLAlchemy 2.x + PostgreSQL 16.11。
- Rationale: FastAPI 强契约与自动 OpenAPI；SQLAlchemy 对事务与锁控制成熟；PostgreSQL 16.11 在并发控制、约束能力与 JSONB 查询上更适配复杂交易域。
- Alternatives considered:
  - Django REST Framework：功能全但相对重，领域分层成本更高。
  - Flask + 插件：灵活但规范一致性和治理成本更高。

## Decision 3: Python environment management

- Decision: 在 `backend/` 使用 `uv venv` 创建并管理虚拟环境，依赖通过 `uv sync` 锁定。
- Rationale: 安装快、可重现性高，适合 CI 与团队一致开发环境。
- Alternatives considered:
  - pip + venv：可行但解析和锁定能力弱于 uv。
  - poetry：功能丰富，但团队已明确 uv 约束。

## Decision 4: Migration and schema governance

- Decision: 使用 Alembic 管理 PostgreSQL schema migration，采用 expand/contract 迁移策略。
- Rationale: 与 SQLAlchemy 原生集成，支持审计字段、幂等约束等逐步演进。
- Alternatives considered:
  - 手写 SQL 迁移：可控但版本一致性与回滚治理成本高。
  - 启动时自动建表：生产风险高，不可审计。

## Decision 5: Idempotency and concurrency safety

- Decision: 写接口统一要求 `Idempotency-Key`，结合 PostgreSQL 唯一约束、事务与 `SELECT ... FOR UPDATE` 行级锁处理；本阶段不引入 Redis。
- Rationale: 保障退款、扣次、冻结/解冻等高风险操作“最多一次生效”，并保持架构最小化。
- Alternatives considered:
  - 仅前端按钮防抖：无法覆盖重试与并发请求。
  - 仅内存去重：服务重启后失效，不满足审计与一致性要求。

## Decision 6: Audit and traceability baseline

- Decision: 关键动作写入 append-only `audit_log`，并贯通 `trace_id`（前端 BFF -> 后端 API）。
- Rationale: 满足按会员时间线追溯、越权拒绝留痕、纠纷可回放。
- Alternatives considered:
  - 仅应用日志：检索与业务语义不足。
  - 仅成功事件留痕：无法解释失败与拒绝路径。

## Decision 7: Authorization model

- Decision: 服务端 RBAC 作为唯一授权真相源；前端 Nuxt middleware 仅做体验层拦截。
- Rationale: 符合宪章“服务端鉴权不可替代”，并保留良好路由体验。
- Alternatives considered:
  - 前端权限控制为主：存在越权风险。
  - 仅后端控制：安全但前端体验较差。

## Decision 8: Domain rule clarifications

- Decision: 保持规格澄清结论：软删除、FEFO 扣卡、冻结顺延、跨会员仅管理员、到期前 7 天提醒。
- Rationale: 与验收场景和宪章一致，且可直接转化为测试用例与合同约束。
- Alternatives considered:
  - FIFO 扣卡或手工选卡：争议与一致性风险更高。
  - 物理删除会员：破坏审计链路。

## Decision 9: Testing strategy

- Decision: 后端采用 `pytest + httpx + testcontainers(postgresql) + schemathesis`；前端采用 `Vitest + Playwright`。
- Rationale: 同时覆盖单元、集成、契约与端到端，验证幂等与权限边界。
- Alternatives considered:
  - SQLite 替代 PostgreSQL：锁语义与事务行为不一致。
  - 仅 API 手工测试：难以保障回归稳定性。
