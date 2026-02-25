<!--
Sync Impact Report
- Version change: template -> 1.0.0
- Modified principles:
  - 模板占位原则 1 -> I. 角色与权限隔离（非妥协）
  - 模板占位原则 2 -> II. 卡项核销一致性（非妥协）
  - 模板占位原则 3 -> III. 预约并发与幂等（非妥协）
  - 模板占位原则 4 -> IV. 可观测与可追溯
  - 模板占位原则 5 -> V. 验收先行
- Added sections:
  - 附加约束
  - 开发流程
- Removed sections:
  - 无
- Templates requiring updates:
  - ✅ updated: .specify/templates/plan-template.md
  - ✅ updated: .specify/templates/spec-template.md
  - ✅ updated: .specify/templates/tasks-template.md
  - ✅ updated: .specify/templates/commands/*.md（目录不存在，无需变更）
  - ✅ reviewed: docs/prd.md（与宪章一致，无需变更）
- Follow-up TODOs:
  - 无
-->
# Yoga Sys Constitution

## Core Principles

### I. 角色与权限隔离（非妥协）
管理员、教练、会员权限 MUST 硬隔离。任何接口 MUST 在服务端执行身份鉴权与
资源归属校验，且 MUST 拒绝越权读写请求。前端显示控制不能替代服务端授权决策。
理由：角色边界是业务与合规底线，任何越权都会直接破坏数据可信性与隐私安全。

### II. 卡项核销一致性（非妥协）
团课与私教 MUST 统一采用“预约预扣、签到实扣、取消返还”规则模型，禁止为单一
课程类型引入冲突口径。缺勤扣次策略与取消窗口 MAY 配置，但每次规则命中与扣返
结果 MUST 可审计、可回放。
理由：统一核销模型是财务口径一致、争议可裁定和报表可对账的前提。

### III. 预约并发与幂等（非妥协）
系统 MUST 保证满员控制、同时间段仅 1 节课限制、重复签到/取消幂等处理。所有
扣次与返还操作 MUST 事务化并具备全链路追踪标识，确保并发下不超卖、不重扣、
不漏返。
理由：预约类业务天然高并发，幂等与事务是防止账实不一致的基础控制。

### IV. 可观测与可追溯
关键业务事件 MUST 记录操作日志，至少覆盖：购卡、续费、退款、预约、取消、签到、
核销、冻结、解冻。系统 MUST 支持按会员与时间线检索事件，并能关联操作人、
时间、对象、前后状态。
理由：可追溯性直接决定运营排障效率、纠纷处理能力与审计可用性。

### V. 验收先行
每个功能 MUST 绑定可测试验收条件，至少覆盖正常流、边界流、异常流，并 MUST
与 PRD 验收标准逐条映射。未满足映射完整性与测试可执行性的需求不得进入开发。
理由：验收先行可降低返工率，确保交付结果可验证、可复盘、可签收。

## 附加约束

1. 到期或无可用卡项的会员 MUST 不可约课。
2. 课前 N 小时 MUST 不可取消，N 为可配置参数且需审计配置变更。
3. 私教已预约时段 MUST 不可重复预约。
4. 报表统计口径 MUST 与业务流水一致，并 MUST 支持导出。

## 开发流程

需求实现 MUST 严格按以下顺序执行，不得跳步：

1. `/speckit.specify`
2. `/speckit.clarify`
3. `/speckit.plan`
4. `/speckit.tasks`
5. `/speckit.implement`

## Governance

1. 本宪章优先级高于项目内其他流程性文档；冲突时以本宪章为准。
2. 宪章版本号 MUST 采用语义化版本：
   - MINOR：新增原则或新增治理章节。
   - MAJOR：原则重定义、移除或引入不兼容治理变更。
   - PATCH：仅文案澄清、错别字修订、非语义调整。
3. 所有日期 MUST 使用 `YYYY-MM-DD` 格式。
4. 若关键信息缺失，文档 MUST 使用 `TODO(字段名): 说明` 标记并在评审中关闭。
5. 每次 `/speckit.plan` 与 PR 评审 MUST 执行宪章合规检查，覆盖权限隔离、核销一致性、
   并发幂等、可追溯与验收映射五项原则。
6. 任何违反“非妥协”原则的实现方案 MUST 在进入开发前被拒绝或重构。

**Version**: 1.0.0 | **Ratified**: 2026-02-24 | **Last Amended**: 2026-02-24
