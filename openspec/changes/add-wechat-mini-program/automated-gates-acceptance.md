# 第十大项验收记录 - Automated security and regression gates

**日期**: 2026-08-11

## 10.1 并发与重放不变量

使用独立 PostgreSQL 连接执行以下测试：

```bash
TEST_DATABASE_URL="postgresql+psycopg://yoga:yoga123@127.0.0.1:5432/yoga_sys_test" \
  uv run pytest -q \
  tests/integration/test_class_booking_concurrency.py \
  tests/integration/test_account_booking_loop.py \
  tests/integration/test_private_slot_reliability.py \
  tests/integration/test_wechat_identity.py \
  tests/integration/test_wechat_auth.py
```

结果：32 项通过。

覆盖最后席位竞争、重复预约、取消与签到终态竞争、微信身份/账号/ticket 竞争、私教时段 create/update/cancel 重放、响应丢失后的同 key 重试，以及不携带 key 的现有浏览器调用。数据库唯一约束、行锁、事务 advisory lock、权益与容量变更均保持单次生效。

## 10.2 敏感数据边界

- structlog 增加递归键级脱敏，覆盖 Authorization、AppSecret、密码、JWT/access token、binding ticket、OpenID、`session_key` 和 identity pepper。
- `business_span` 对敏感属性名写入 `[REDACTED]`。
- middleware canary 测试证明请求 header、query 和 body 不进入日志或 span，仅记录 method、path、status、duration 和 trace/span ID。
- 生产源码扫描拒绝嵌入 AppSecret、identity pepper 和 JWT 字面量。
- 后端认证响应、数据库摘要和审计白名单由认证、identity、解绑及脱敏测试共同覆盖。
- 小程序日志不记录 token、密码或请求体；存储只允许 JWT 位于 `yoga.auth.token`，短期 ticket 位于绑定状态，密码、微信 code、OpenID 和 `session_key` 不落盘。

专项结果：后端 39 项通过，小程序 API/session/idempotency 11 项通过。

## 10.3 后端门禁

| 门禁 | 结果 |
|---|---|
| `uv run pytest -q` | 255 passed, 1 skipped，覆盖率 89% |
| PostgreSQL integration | 通过 |
| OpenAPI contract | 通过，包含在完整套件中 |
| `uv run ruff check app tests` | 通过 |
| `uv run mypy` | 通过，检查 11 个微信认证、持久化和观测关键模块 |
| `uv run python -m compileall -q app` | 通过 |
| Alembic heads/current | 唯一 `0008_wechat_identity` head |
| `0008 -> 0007 -> 0008` | 通过 |

已修复 `test_member_self_service_cards.py` 对运行日期的隐式依赖，测试现在通过业务时钟 dependency override 固定日期。Ruff 对整个 `app/tests` 执行语法和未使用符号门禁；MyPy 首次引入时聚焦本变更安全关键模块，未通过忽略错误隐藏微信实现问题。

## 10.4 小程序门禁

| 门禁 | 结果 |
|---|---|
| `npm run lint` | 通过 |
| `npm run typecheck` | 通过 |
| `npm test` | 9 files / 31 tests passed |
| Page interaction | 绑定重复点击、预约重复点击与权威刷新通过 |
| `npm run build` | 通过 |

构建脚本除 TypeScript 检查外，验证微信 TypeScript compiler plugin、minification、16 个注册页面、1 个本地组件及其 TS/JSON/WXML/WXSS 资源。该门禁不需要上传私钥；微信体验版上传、真实 `code2Session` 和真机验证仍属于任务 11。

## 10.5 Nuxt 回归门禁

| 门禁 | 结果 |
|---|---|
| `npm run lint` | 通过 |
| `npm run typecheck` | 通过 |
| `npm run test:unit` | 9 files / 23 tests passed |
| `npm run test:e2e` | 11 passed |
| `npm run build` | 通过 |

修正一条历史 Playwright 场景，使其按当前会员页面先进入“业务管理”再开通账号。管理员、会员、教练、团课、私教、报表和账号管理工作流均通过，Nuxt cookie/BFF 流程未被小程序 Bearer 认证路径破坏。

## 结论

任务 10.1-10.5 全部通过，fake provider 与本地/test FastAPI 的开发版自动化门禁闭环。任务 11.2-11.8 继续作为生产基础设施、主体资质、真实 provider、真机和提审里程碑，不因本报告而视为完成。
