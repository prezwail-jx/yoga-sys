# Data Model: member-card-core

## 1) Member（会员）

### Fields
- `id` (UUID, PK)
- `name` (string, 1-50)
- `gender` (enum: male/female/other/unknown)
- `phone` (string, unique)
- `birthday` (date, nullable)
- `note` (string, nullable)
- `join_date` (date)
- `emergency_contact` (string, nullable)
- `status` (enum: normal/paused/expired/disabled)
- `deleted_at` (timestamp, nullable)  // 软删除标记
- `created_at` / `updated_at` (timestamp)

### Rules
- `phone` 全局唯一。
- 软删除后不得再发起新交易或新预约预扣。
- 会员仅可查询本人记录；跨会员查询仅管理员。

## 2) CardProduct（卡项定义）

### Fields
- `id` (UUID, PK)
- `name` (string, 1-100)
- `card_type` (enum: duration/times/private/trial)
- `price` (decimal >= 0)
- `cost_price` (decimal >= 0, nullable)
- `total_times` (int >= 0, nullable)
- `valid_days` (int >= 0, nullable)
- `activation_mode` (enum: immediate/first_booking)
- `applicable_course_scope` (enum: group/private/specific)
- `specific_course_ids` (jsonb array, nullable)
- `absence_deduct_enabled` (bool)
- `cancel_refund_enabled` (bool)
- `enabled` (bool)
- `created_at` / `updated_at` (timestamp)

### Rules
- `duration` 卡必须有 `valid_days`。
- `times`/`private`/`trial`（按次）卡必须有 `total_times`。
- 当 `applicable_course_scope=specific` 时，`specific_course_ids` 不能为空。

## 3) MemberCard（会员持卡实例）

### Fields
- `id` (UUID, PK)
- `member_id` (FK -> Member.id)
- `card_product_id` (FK -> CardProduct.id)
- `status` (enum: pending_activation/active/frozen/expired/closed)
- `opened_at` (timestamp, nullable)
- `expires_at` (timestamp, nullable)
- `remaining_times` (int >= 0, nullable)
- `used_times` (int >= 0, default 0)
- `frozen_from` / `frozen_to` (timestamp, nullable)
- `total_frozen_days` (int >= 0, default 0)
- `remind_at` (timestamp, nullable) // 到期前 7 天
- `created_at` / `updated_at` (timestamp)

### Rules
- 冻结期间暂停计时，解冻后 `expires_at` 顺延 `frozen_days`。
- FEFO 选择核销目标卡：按 `expires_at ASC`，同值按 `opened_at ASC`。
- 过期或 `remaining_times=0` 不可参与新预扣。

## 4) CardTransaction（卡项交易流水）

### Fields
- `id` (UUID, PK)
- `member_id` (FK -> Member.id)
- `member_card_id` (FK -> MemberCard.id, nullable)
- `txn_type` (enum: purchase/renew/reissue/refund/freeze/unfreeze/extend)
- `amount` (decimal, nullable)
- `times_delta` (int, nullable)
- `valid_days_delta` (int, nullable)
- `idempotency_key` (string)
- `trace_id` (string)
- `operator_id` (string)
- `operator_role` (enum: admin/coach/member/system)
- `occurred_at` (timestamp)
- `created_at` (timestamp)

### Rules
- `idempotency_key + txn_type + member_id` 唯一。
- 退款必须引用原交易（可在扩展字段记录 `origin_txn_id`）。

## 5) WriteOffEvent（核销事件）

### Fields
- `id` (UUID, PK)
- `member_id` (FK -> Member.id)
- `member_card_id` (FK -> MemberCard.id)
- `event_type` (enum: reserve_hold/checkin_commit/cancel_refund)
- `business_ref` (string) // 预约单号/签到单号
- `times_delta` (int) // 预扣/实扣为负，返还为正
- `selection_basis` (string) // FEFO 命中说明
- `idempotency_key` (string)
- `trace_id` (string)
- `operator_id` (string)
- `operator_role` (enum: admin/coach/member/system)
- `occurred_at` (timestamp)

### Rules
- 同 `business_ref + event_type` 唯一，保证重复签到/取消幂等。
- 仅允许链路顺序：`reserve_hold` -> `checkin_commit` 或 `cancel_refund`。

## 6) AuditLog（操作审计日志）

### Fields
- `id` (UUID, PK)
- `trace_id` (string)
- `idempotency_key` (string, nullable)
- `action` (enum: purchase/renew/refund/reserve/cancel/checkin/writeoff/freeze/unfreeze/member_update/member_delete)
- `operator_id` (string)
- `operator_role` (enum: admin/coach/member/system)
- `member_id` (UUID, nullable)
- `object_type` (string)
- `object_id` (string)
- `before_state` (jsonb, nullable)
- `after_state` (jsonb, nullable)
- `result` (enum: success/rejected/failed)
- `reason` (string, nullable)
- `occurred_at` (timestamp)

### Rules
- 审计日志必须覆盖宪章要求事件集合。
- 拒绝越权操作必须落日志，`result=rejected`。

## 7) IdempotencyRecord（幂等记录）

### Fields
- `id` (bigint, PK)
- `scope` (string) // endpoint or action scope
- `actor_id` (string)
- `idempotency_key` (string)
- `request_hash` (string)
- `response_code` (int)
- `response_body` (jsonb)
- `created_at` (timestamp)
- `expires_at` (timestamp)

### Rules
- 唯一键：`scope + actor_id + idempotency_key`。
- 若同 key 且 `request_hash` 不同，返回冲突错误。
- 默认保留至少 24 小时用于重试去重。

## 8) RoleBinding（角色绑定）

### Fields
- `id` (UUID, PK)
- `user_id` (UUID)
- `role` (enum: admin/coach/member)
- `member_id` (UUID, nullable) // role=member 时绑定本人
- `coach_profile_id` (UUID, nullable) // role=coach 时用于资源归属
- `created_at` (timestamp)

### Rules
- 一个用户可多角色，但查询范围由后端策略收敛。
- 跨会员完整记录查询仅 `admin` 允许。

## Relationships
- Member 1..N MemberCard
- CardProduct 1..N MemberCard
- Member 1..N CardTransaction
- MemberCard 1..N WriteOffEvent
- Member 1..N AuditLog
- Member 1..N IdempotencyRecord (by actor or bound user)

## State Transitions

### MemberCard
- `pending_activation -> active`（立即开卡或首次预约触发）
- `active -> frozen`（冻结）
- `frozen -> active`（解冻并顺延）
- `active/frozen -> expired`（到期）
- `active/expired -> closed`（退款关闭/运营关闭）

### Member
- `normal <-> paused`
- `normal/paused -> disabled`
- `normal/paused -> expired`（无有效卡项时可派生标记）

## Data Volume & Indexing Assumptions
- 会员量级 1k-20k，交易与核销事件日新增 5k 左右。
- 数据库基线：PostgreSQL 16.11。
- 建议索引：
  - `member(phone)` unique
  - `member_card(member_id, status, expires_at)`
  - `card_transaction(member_id, occurred_at desc)`
  - `writeoff_event(member_id, occurred_at desc)`
  - `audit_log(member_id, occurred_at desc)`
  - `idempotency_record(scope, actor_id, idempotency_key)` unique
  - `role_binding(user_id, role)`
