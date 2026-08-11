# 基线验收报告 — add-wechat-mini-program

**日期**: 2026-08-05  
**Git SHA**: `5d6f86b`  
**分支**: `002-member-card-core`

## 环境

| 项目 | 版本 |
|---|---|
| Python | 3.12.3 (GCC 13.3.0) |
| Node | v24.13.0 |
| PostgreSQL | 16.14 (Ubuntu) |
| 测试数据库 | `yoga_sys_test` |
| 开发数据库 | `yoga_sys` |

## 1.1 账号基线（improve-account-member-admin-flows）

来源变更的全部 23 项任务均已勾选完成，覆盖：

- 管理员重置会员/教练密码
- 会员自行修改密码
- 禁用会员重新启用
- 账号开通 UX（重复用户名、已绑定状态）
- 会员列表账号状态栏（has_account/username/操作按钮）
- 私教错误处理
- 审计、权限和密码泄漏防护

1.1 保持已勾选。

## 1.2 迁移与验收

### 迁移检查

```bash
DATABASE_URL="postgresql+psycopg://yoga:yoga123@127.0.0.1:5432/yoga_sys_test" uv run alembic upgrade head
DATABASE_URL="postgresql+psycopg://yoga:yoga123@127.0.0.1:5432/yoga_sys_test" uv run alembic heads
DATABASE_URL="postgresql+psycopg://yoga:yoga123@127.0.0.1:5432/yoga_sys_test" uv run alembic current
```

| 检查项 | 结果 |
|---|---|
| alembic upgrade | ✅ 成功 |
| heads | `0007_private_training_reporting (head)` — 唯一 |
| current | `0007_private_training_reporting (head)` — 与 heads 一致 |

### 后端专项测试

```bash
TEST_DATABASE_URL="postgresql+psycopg://yoga:yoga123@127.0.0.1:5432/yoga_sys_test" uv run pytest -q \
  tests/unit/test_account_binding_auth.py \
  tests/integration/test_account_admin_flows.py \
  tests/unit/test_private_training_service.py \
  tests/unit/test_reporting_service.py
```

| 文件 | 结果 |
|---|---|
| `test_account_binding_auth.py` | ✅ |
| `test_account_admin_flows.py` | ✅ |
| `test_private_training_service.py` | ✅ |
| `test_reporting_service.py` | ✅ |

**专项合计**: 32 passed, 0 failed

### 后端完整套件

```bash
TEST_DATABASE_URL="postgresql+psycopg://yoga:yoga123@127.0.0.1:5432/yoga_sys_test" uv run pytest -q
```

| 项目 | 结果 |
|---|---|
| 通过 | 所有业务测试 |
| 失败 | 8 项（全部为 `test_group_class_contract.py`） |
| 跳过 | 1 项（性能测试，未配置 `PERF_DATABASE_URL`） |
| 覆盖率 | 85% |

**历史问题 — test_group_class_contract.py（8 项失败，已解决）**

```text
FileNotFoundError: openspec/changes/group-class-booking-loop/contracts/group-class-booking.openapi.yaml
```

原因：合约文件在 `/archive/2026-07-21-group-class-booking-loop/contracts/` 中，但测试仍引用旧路径 `openspec/changes/group-class-booking-loop/contracts/`。后续已将权威合约复制到稳定路径 `specs/contracts/group-class-booking.openapi.yaml`，测试不再依赖带日期的归档目录。

### 前端验收

| 命令 | 结果 |
|---|---|
| `npm run lint` | ✅ 通过 |
| `npm run typecheck` | ✅ 通过 |
| `npm run test:unit` | ✅ 9 文件 / 22 测试 全部通过 |
| `npm run test:e2e -- private-training-reporting.spec.ts us1.spec.ts` | ✅ 7 测试 全部通过 |
| `npm run build` | ✅ 构建成功（Tailwind sourcemap 非阻断警告） |

### 可分配下一条 Alembic revision

✅ `0007_private_training_reporting` 是唯一 head，基线稳定。可以在此之上分配 `0008`（微信身份与绑定挑战表）。

## 1.3 域名与服务器基线

| 项 | 状态 |
|---|---|
| 根域名 | `tuitukj.com`（已备案） |
| API 域名 | `yoga.tuitukj.com` |
| DNS A 记录 | → `124.220.91.149` |
| HTTP 可达 | ✅ Nginx 默认页 |
| HTTPS 可用 | ❌ TLS 握手失败 |
| FastAPI 反向代理 | 待部署 |
| PostgreSQL 备份 | 待配置 |

确认项已完成，部署缺口已记录，归属后续 `11.2`。

## 1.4 主体与 AppID

| 项 | 值 |
|---|---|
| 当前 AppID | `wx9fc61b966bf4e207` |
| 主体 | 个人 |
| 用途 | 开发版真实登录 / 开发工具调试 |
| 商用发布 | 需要企业或个体工商户主体，注册新生产 AppID |
| 生产 AppID | 待定，记作 `TBD` |

## 1.5 微信后台门槛

全部标记为延期生产门槛，后续在非个人主体控制台中确认。1.5 保持已勾选。

## 1.6 配置决策

参见 `design.md` 第 9 节已更新的配置表。关键决策：

- 开发 AppID `wx9fc61b966bf4e207`（个人主体）用于开发版真实登录
- 生产 AppID 待非个人主体注册后确定
- 本地开发 `backend/.env`，生产 `/etc/yoga-sys/backend.env:0600`
- JWT 60 分钟，绑定挑战 10 分钟 / 5 次最大失败
- 微信 API 超时 5 秒
- `WECHAT_PROVIDER=fake` 用于自动化测试，`real` 用于真实微信对接
- 生产环境禁止 `WECHAT_PROVIDER=fake`

## 结论

第一大项的基线验收通过。`0007` 是唯一稳定的迁移 head，账号/私教/报表业务逻辑和前后端测试均无回归。下一阶段可以分配 `0008` 迁移，开始微信身份和绑定挑战表的开发。

### 未修复但已记录的已知问题

| # | 问题 | 影响 | 建议 |
|---|---|---|---|
| 1 | `test_group_class_contract.py` 8 项失败，合约文件路径指向已归档目录 | 合约校验 CI 中断 | 更新 `tests/contract/test_group_class_contract.py:12` 的 `CONTRACT_PATH` 指向 archive 副本 |
