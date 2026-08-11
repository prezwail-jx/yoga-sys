# 微信小程序自动化安全与回归门闭环

**时间**: 2026-08-11 09:38:33 CST

## 变更点

1. 验证重复和并发小程序写操作保持预约、核销、私教、行锁与幂等不变量。
2. 扩展敏感数据检查，覆盖源码、响应、结构化日志、trace、审计记录和小程序存储边界。
3. 修复本变更引入或暴露的后端回归，执行单元、PostgreSQL 集成、迁移、OpenAPI、lint 和类型检查。
4. 补齐小程序页面交互测试并执行 lint、类型检查、测试和可复现构建。
5. 执行 Nuxt 单元、Playwright、lint、类型检查和生产构建，确认浏览器工作流不受影响。
6. 将结果记录到 OpenSpec 验收报告，并仅在对应门禁通过后勾选任务 10.1-10.5。

## 测试计划

- 后端：`uv run pytest -q`，并针对并发、重放、微信认证、脱敏与 OpenAPI 场景执行专项回归。
- 迁移：执行 `0008 -> 0007 -> 0008` 往返并确认唯一 head。
- 后端静态检查：执行项目配置的 lint、类型检查和 `compileall`。
- 小程序：执行 `npm run lint`、`npm run typecheck`、`npm test` 和 `npm run build`。
- Nuxt：执行 `npm run lint`、`npm run typecheck`、`npm run test:unit`、`npm run test:e2e` 和 `npm run build`。
- OpenSpec：执行 `openspec validate add-wechat-mini-program`。

## 假设与风险

- 本次只闭合开发版任务 10.1-10.5；任务 11.2-11.8 继续作为生产延期里程碑。
- PostgreSQL 集成测试使用独立测试数据库，禁止对开发或生产数据库执行迁移往返。
- 微信开发者工具或上传私钥不可用时，只能证明仓库内可复现构建；真实设备和体验版验收仍归任务 11。
- 当前小程序 `build` 与类型检查可能等价，需要调整为能够产出可供微信开发者工具加载的编译目录或明确记录工具边界。
- Playwright 依赖本机浏览器与服务启动能力；若环境缺失，先尝试恢复依赖，仍不可用则保留任务未完成并记录阻塞。

## 结果总结

- 10.1：32 个 PostgreSQL 并发与重放场景通过，预约、核销、私教、锁与幂等不变量闭环。
- 10.2：增加统一日志/span 脱敏、middleware canary、源码扫描和客户端存储边界测试；专项测试全部通过。
- 10.3：修复会员卡固定日期回归；后端完整套件 255 passed、1 skipped，覆盖率 89%；Ruff、MyPy、compileall、OpenAPI 和 Alembic 往返通过。
- 10.4：小程序 9 文件 31 测试通过，新增 Page 交互测试和 16 页面/1 组件包结构构建校验。
- 10.5：Nuxt 9 文件 23 单测、11 个 Playwright 场景、lint、typecheck 和 production build 通过。
- 验收证据写入 `openspec/changes/add-wechat-mini-program/automated-gates-acceptance.md`，任务 10.1-10.5 已勾选。

## 后续跟进

- Task 11.2-11.8 仍需生产服务器 TLS/反代/备份、非个人主体、合法域名、真实 `code2Session`、iOS/Android 真机、体验版和提审能力。
- MyPy 当前覆盖本变更的 11 个安全关键模块；后续可单独建立技术债任务，逐步扩展到完整后端，避免与小程序交付混合。
- 微信开发者工具上传和真机编译需要私钥/登录态，继续归入生产发布里程碑。
