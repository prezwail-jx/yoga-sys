# US1 验收报告

**执行日期**：2026-07-16
**范围**：T016–T030（会员与卡项基础资料 MVP）

## 结果

- 后端：15 项测试通过，PostgreSQL 16 + Alembic，覆盖率 83%。
- 前端单元测试：2 项通过。
- 前端 E2E：2 项通过，覆盖管理员进入会员管理和教练无权限流程。
- ESLint：通过。
- Nuxt 严格类型检查：通过。
- Nuxt 生产构建：通过。

## 已验收能力

- 管理员/教练密码登录与 JWT 角色识别。
- 会员新增、搜索、分页、编辑、状态转换与软删除。
- 卡项模板新增、查询、规则编辑与启停。
- 卡类型、次数、有效期和指定课程条件校验。
- 教练写操作返回 403，并写入 rejected 审计日志。
- Nuxt 通过 HttpOnly Cookie 和 BFF 调用 FastAPI。
- 团课、私教和报表继续使用 Mock，并在导航中标识。

## 环境说明

当前执行环境无法从宿主进程访问 Docker 映射端口，因此后端验收在 PostgreSQL 容器网络内执行。测试夹具同时支持常规 Testcontainers 模式和通过 `TEST_DATABASE_URL` 指定已有测试库。

---

# US2 验收报告

**执行日期**：2026-07-16
**范围**：T031–T045（卡项交易与生命周期）

## 结果

- 后端完整套件：26 项通过，覆盖率 90%。
- US2 集成测试：10 项通过，覆盖正常、边界、异常和幂等重放。
- 前端单元测试：4 项通过，其中幂等提交组件 2 项。
- 前端 E2E：3 项通过，其中卡项办理流程 1 项。
- ESLint、Nuxt 严格类型检查、OpenAPI YAML 解析和 `git diff --check`：通过。
- Alembic 当前版本：`0003_member_card_transactions (head)`。

## 已验收能力

- 购卡、续费、补卡、整笔退款和人工延期。
- 首次约课待激活与购卡立即开卡。
- 上海自然日到期计算、提前 7 天提醒和访问时状态校准。
- 冻结、提前解冻、冻结截止日自动解冻和有效期顺延。
- 卡项模板购买快照，模板修改不反向影响已购权益。
- PostgreSQL advisory lock、幂等响应重放和同 key 不同载荷冲突保护。
- 会员中心式卡项办理页、会员快捷入口和生命周期操作面板。

## 环境说明

当前沙箱无法访问 Docker Testcontainers 映射端口，因此最终后端验收使用本机 PostgreSQL，通过 `TEST_DATABASE_URL` 显式连接；测试数据均处于每用例外层事务并在结束时回滚，外部数据库模式禁止执行 `downgrade base`。数据库仅保留正常的 Phase 4 向前迁移。

## 已知警告

本地 `.env` 中 JWT HMAC 密钥长度不足 32 字节，测试会产生 `InsecureKeyLengthWarning`。部署前必须将 `JWT_SECRET` 替换为至少 32 字节的随机密钥。

---

# Phase 6 阶段验收记录

**执行日期**：2026-07-17
**范围**：T059–T063（可观测性、数据库优化、运行手册与异步状态）

## 已通过

- OpenTelemetry 观测性单元测试：1 项通过。
- Alembic：`0005_perf_indexes (head)` 已成功应用于开发库。
- PostgreSQL：`pg_trgm`、4 个核心性能索引及 3 个数据约束已核对存在。
- 前端单元测试：6 项通过。
- 前端 E2E：4 项通过，覆盖 US1/US2/US3。
- ESLint：0 错误、0 警告。
- Nuxt 严格类型检查：通过。
- Nuxt 生产构建：通过。

## 首次验收阻塞（已解决）

后端完整套件首次运行结果为 6 项通过、30 项环境错误；错误均发生在 Testcontainers 随机映射端口连接超时，未进入业务断言。开发库不能用于会清表的验收测试。本机目前只有 `postgres` 和 `yoga_sys`，且 `yoga` 角色无 `CREATEDB` 权限，因此需要管理员创建独立的 `yoga_sys_test` 后再执行最终后端套件。

## 复验命令

```bash
sudo -u postgres createdb -O yoga yoga_sys_test
cd backend
TEST_DATABASE_URL=postgresql+psycopg://yoga:yoga123@127.0.0.1:5432/yoga_sys_test uv run pytest -q
```


## 最终复验（阻塞已解除）

- 独立测试数据库：yoga_sys_test，未影响开发数据。
- 后端完整套件：36 项全部通过。
- 总体测试覆盖率：92%。
- 健康检查本机采样 50 次：p95 为 4.34 ms（记录项，不作为 CI 硬门禁）。
- T059–T063 均已完成，Phase 6 验收通过。
