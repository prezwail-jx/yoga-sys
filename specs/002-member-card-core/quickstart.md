# Quickstart: member-card-core

## 目标

验证本 feature 的关键验收路径是否满足宪章与 PRD 映射：
- 角色隔离（管理员/教练/会员）
- 统一核销链路（预约预扣 -> 签到实扣 -> 取消返还）
- 并发幂等（重复提交不重复生效）
- 审计追溯（关键事件可按会员时间线回放）

## 环境初始化

### Backend（Python 3 + uv + PostgreSQL）

```bash
mkdir -p backend
cd backend
uv venv
source .venv/bin/activate
uv init --python 3.12
uv add fastapi "uvicorn[standard]" pydantic sqlalchemy alembic "psycopg[binary]" structlog opentelemetry-sdk
uv add --dev pytest pytest-cov httpx schemathesis testcontainers
```

> 数据库建议：PostgreSQL 16.11，本地可用 Docker 启动并创建 `yoga_sys` 库。
>
> 本阶段不使用 Redis。

### Frontend（Nuxt 3 + dashboard-vue 风格）

```bash
mkdir -p frontend
cd frontend
npx nuxi@latest init .
npm install
npm install @nuxt/ui
```

> 页面结构与交互参考 `https://github.com/nuxt-ui-templates/dashboard-vue`，在 Nuxt 中实现侧边栏、仪表盘、列表过滤与详情抽屉模式。

## 前置数据

1. 创建 1 个管理员账号、1 个教练账号、2 个会员账号（A/B）。
2. 创建 2 张卡项模板：
   - 次数卡（10 次，立即开卡）
   - 体验卡（3 次，首次预约开卡）
3. 为会员 A 办理两张可用卡，设置不同到期日（用于 FEFO 验证）。

## 验收步骤

### 场景 1：会员与卡项主数据（正常）

1. 管理员新增会员 A，并更新其状态为 `normal`。
2. 管理员新增卡项模板并保存核心字段。
3. 预期：新增/编辑成功，可查询。

### 场景 2：角色隔离（异常）

1. 教练尝试编辑会员 A 基础资料。
2. 会员 B 尝试读取会员 A 时间线。
3. 预期：均被拒绝，且生成 `result=rejected` 审计日志。

### 场景 3：交易与状态变更（正常 + 边界）

1. 管理员为会员 A 执行购卡、续费。
2. 冻结会员 A 某卡，再解冻。
3. 预期：冻结期间暂停计时；解冻后到期日按冻结天数顺延。

### 场景 4：核销链路一致性（正常）

1. 对同一业务单执行 `reserve_hold`。
2. 执行 `checkin_commit`。
3. 对另一业务单执行 `reserve_hold` 后 `cancel_refund`。
4. 预期：链路完整且顺序合法。

### 场景 5：并发幂等（异常）

1. 对同一退款请求并发提交两次（同 `Idempotency-Key`）。
2. 对同一签到请求重复提交两次（同业务引用）。
3. 预期：仅第一次改变状态，后续返回幂等结果，不重复扣返。

### 场景 6：多卡 FEFO 选择（边界）

1. 会员 A 拥有两张可扣减卡，分别设置到期日 D1 < D2。
2. 执行一次预扣。
3. 预期：优先命中 D1 卡；若 D1 与 D2 同到期，则命中更早开卡卡。

### 场景 7：过期约束（边界）

1. 将会员 A 卡项推进到到期或次数为 0。
2. 发起新的预扣请求。
3. 预期：请求被拒绝。

## PRD 映射核对

1. 对照 `spec.md` 的 `PRD Acceptance Mapping` 逐条打勾。
2. 每条至少有 1 个正常流和 1 个边界/异常流用例证据。

## 通过标准

- 所有场景预期结果满足。
- 时间线可检索到购卡、续费、退款、预扣、实扣、返还、冻结、解冻全量记录。
- 未出现越权成功、重复扣次、重复退款、链路乱序。

## US1 当前可运行方式（2026-07-16）

### 后端

```bash
cd backend
uv sync
alembic upgrade head
python -m app.scripts.seed_users
uvicorn app.main:app --reload
```

账号从 `.env` 读取；开发默认值为 `admin/admin123` 和 `coach/coach123`。生产环境必须替换 `JWT_SECRET` 和所有初始密码。

### 前端

```bash
cd frontend
npm install
NUXT_BACKEND_BASE_URL=http://127.0.0.1:8000 npm run dev
```

访问 `http://127.0.0.1:3000/login`。会员和卡项通过 Nuxt BFF 使用真实后端；课表、私教和报表仍为 Mock。

### US1 验证命令

```bash
cd backend
uv run pytest -q

cd ../frontend
npm test
npm run lint
npm run typecheck
npm run build
```

Testcontainers 无法访问宿主映射端口的受限环境，可设置 `TEST_DATABASE_URL`，并在与 PostgreSQL 相同的 Docker 网络中执行 pytest。上文场景 3–7 属于 US2/US3，尚未在本轮交付。
