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

预期分别看到 `{"status":"ok"}` 和 `0006_group_class_booking (head)`。

## 3. 启动前端

另开终端：

```bash
cd frontend
npm install
NUXT_BACKEND_BASE_URL=http://127.0.0.1:8000 npm run dev
```

访问 `http://127.0.0.1:3000/login`。先使用 `.env` 中管理员账号登录；会员和教练资源账号可由管理员在页面中开通。

## 4. 功能验证

1. 会员管理：新增、编辑、暂停、禁用和归档会员；归档仅软删除，历史记录保留。
2. 卡项管理：创建次数卡、期限卡、私教卡或体验卡，并启停模板；指定课程卡只能保存已存在课程的 UUID。
3. 卡项办理：购卡、续费、补卡、退款、冻结、解冻和延期；重复请求使用同一 `Idempotency-Key` 不会重复生效。
4. 核销：按 `reserve_hold -> checkin_commit` 或 `reserve_hold -> cancel_refund` 顺序处理，卡项按 FEFO 规则选择。
5. 业务时间线：从会员列表进入“业务记录”，核对交易、冻结、核销和审计事件；跨会员越权读取会被拒绝并留痕。
6. 团课基础资料：进入 `/class-catalog` 维护课程、教室和教练，并可为启用教练开通账号。
7. 团课排课：进入 `/schedule` 创建课次、发布、暂停、恢复和复制上周；从课次详情执行代约、签到、取消和结课。
8. 会员账号：在 `/members` 为正常会员开通账号，使用该账号登录后从 `/schedule` 自助预约，并在 `/my-bookings` 查看或按截止规则取消。
9. 角色隔离：教练登录后只显示本人课表；会员导航只显示团课课表和“我的预约”；越权操作仍由后端最终拒绝。

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

## 7. 团课性能与容量记录

性能测试会清空指定性能库，必须由 PostgreSQL 管理员预先创建独立数据库：

```bash
sudo -u postgres createdb -O yoga yoga_sys_perf
cd backend
PERF_DATABASE_URL=postgresql+psycopg://yoga:yoga123@127.0.0.1:5432/yoga_sys_perf \
  PERF_PROFILE=smoke uv run pytest tests/performance/test_group_class_performance.py -s
PERF_DATABASE_URL=postgresql+psycopg://yoga:yoga123@127.0.0.1:5432/yoga_sys_perf \
  PERF_PROFILE=target uv run pytest tests/performance/test_group_class_performance.py -s
```

`smoke` 写入 1,000 名会员并快速验证入口；`target` 写入 20,000 名会员、5,000 个课次和 100,000 条预约。输出记录预约写入 p95 和 50 条时间线查询 p95。测试拒绝任何数据库名不是 `yoga_sys_perf` 的连接。

## 8. 完整验收

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
