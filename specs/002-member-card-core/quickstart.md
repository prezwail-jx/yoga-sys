# Quickstart: member-card-core

## 环境要求

- Python 3.12 与 uv
- Node.js 20 LTS、npm
- PostgreSQL 16（已验证 16.14；设计基线 16.11）
- PostgreSQL 用户需有目标数据库的建表、建索引和 `CREATE EXTENSION pg_trgm` 权限

本项目不依赖 Redis。默认可在没有 OpenTelemetry Collector 的情况下运行。

## 1. 准备 PostgreSQL

示例（请按本机管理员账号执行）：

```sql
CREATE USER yoga WITH PASSWORD 'yoga123';
CREATE DATABASE yoga_sys OWNER yoga;
```

复制环境变量：

```bash
cd backend
cp .env.example .env
```

至少检查以下配置：

```env
DATABASE_URL=postgresql+psycopg://yoga:yoga123@localhost:5432/yoga_sys
JWT_SECRET=请使用至少32字节的随机密钥
ADMIN_USERNAME=admin
ADMIN_PASSWORD=请替换开发默认密码
COACH_USERNAME=coach
COACH_PASSWORD=请替换开发默认密码
```

`.env` 不应提交。生产环境必须替换 JWT 密钥和初始账号密码。

## 2. 启动后端

```bash
cd backend
uv sync
uv run alembic upgrade head
uv run python -m app.scripts.seed_users
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

验证：

```bash
curl http://127.0.0.1:8000/healthz
uv run alembic current
```

预期分别看到 `{"status":"ok"}` 和 `0005_perf_indexes (head)`。

## 3. 启动前端

另开终端：

```bash
cd frontend
npm install
NUXT_BACKEND_BASE_URL=http://127.0.0.1:8000 npm run dev
```

访问 `http://127.0.0.1:3000/login`。使用 `.env` 中管理员或教练账号登录。

## 4. 功能验证

1. 会员管理：新增、编辑、暂停、禁用和归档会员；归档仅软删除，历史记录保留。
2. 卡项管理：创建次数卡、期限卡、私教卡或体验卡，并启停模板。
3. 卡项办理：购卡、续费、补卡、退款、冻结、解冻和延期；重复请求使用同一 `Idempotency-Key` 不会重复生效。
4. 核销：按 `reserve_hold -> checkin_commit` 或 `reserve_hold -> cancel_refund` 顺序处理，卡项按 FEFO 规则选择。
5. 业务时间线：从会员列表进入“业务记录”，核对交易、冻结、核销和审计事件；跨会员越权读取会被拒绝并留痕。

主要接口文档：`http://127.0.0.1:8000/docs`。

## 5. 可观测性

开发环境默认输出可读的结构化日志，并为 HTTP 请求、交易、卡生命周期、核销和时间线查询创建 Span。

```env
LOG_FORMAT=console
OTEL_ENABLED=true
OTEL_SERVICE_NAME=yoga-sys-backend
OTEL_EXPORTER_OTLP_ENDPOINT=
OTEL_TRACES_SAMPLER_ARG=1.0
```

不配置 `OTEL_EXPORTER_OTLP_ENDPOINT` 时不会发送外部数据。若已有兼容 OTLP/HTTP 的 Collector，可填写 traces 端点；例如 `http://localhost:4318/v1/traces`。生产环境建议使用 `LOG_FORMAT=json` 并降低采样率。

## 6. PostgreSQL 优化验证

迁移会启用 `pg_trgm`，并创建会员姓名/手机号模糊检索、会员有效记录、卡模板、卡项 FEFO 和幂等记录过期时间索引，同时增加关键数据约束。

```bash
PGPASSWORD=yoga123 psql -h 127.0.0.1 -U yoga -d yoga_sys -c "\\dx pg_trgm"
PGPASSWORD=yoga123 psql -h 127.0.0.1 -U yoga -d yoga_sys -c "\\di ix_*"
```

## 7. 完整验收

```bash
cd backend
uv run pytest

cd ../frontend
npm test
npm run lint
npm run typecheck
npm run build
npm run test:e2e
```

性能 p95 作为验收记录项，不作为 CI 硬门禁；功能正确性、权限、幂等、迁移和构建失败均属于阻断问题。
