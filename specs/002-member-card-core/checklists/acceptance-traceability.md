# US1/US2 验收追踪矩阵

| 验收场景 | PRD/Spec | 任务 | 自动化证据 |
|---|---|---|---|
| 管理员新增并查询会员 | US1-AS1、PRD 2.1 | T016、T020、T022、T024、T026、T028 | `test_us1_normal_member_cardproduct.py::test_admin_creates_and_queries_member` |
| 管理员创建并维护卡项规则 | US1-AS2、PRD 3.1/3.2 | T016、T021、T023、T025、T027、T029 | `test_admin_creates_and_updates_card_product`、`test_card_product_conditional_fields_are_validated` |
| 禁用会员不可预约 | US1-AS3、PRD 2.1/3.4 | T017、T024 | `test_us1_boundary_member_status.py::test_disabled_member_is_rejected_by_booking_guard` |
| 教练越权写入被拒绝并审计 | US1-AS4、PRD 6.2 | T018、T030 | `test_us1_exception_rbac.py` |
| 会员软删除且手机号不可复用 | Clarification、Data Model 1 | T017、T020、T022、T024、T026 | `test_soft_deleted_phone_cannot_be_reused` |
| 购卡、续费、补卡和延期更新会员权益 | US2-AS1、FR-003/004 | T031、T035-T043 | `test_us2_normal_transactions.py::test_purchase_renew_reissue_and_extend_lifecycle` |
| 冻结、提前解冻与自然日顺延 | US2-AS2、FR-004/012 | T031、T035、T037、T040、T042、T044 | `test_freeze_and_manual_unfreeze_extend_by_natural_days` |
| 到期前 7 天提醒与访问时过期校准 | US2-AS3、FR-005 | T032、T035、T040、T042、T044 | `test_us2_boundary_expiry_freeze.py` |
| 退款重放不重复变更权益 | US2-AS4、FR-010、SC-003 | T033、T036、T038、T039、T041、T045 | `test_refund_replay_returns_same_transaction_without_second_mutation` |
| 同幂等键不同请求被拒绝 | CA-003、FR-010 | T033、T038、T041 | `test_same_idempotency_key_with_different_payload_returns_conflict` |
| 教练办理交易被拒绝 | CA-001、FR-008/009 | T033、T041 | `test_coach_cannot_create_transaction` |

## 验收环境

- PostgreSQL 16 容器。
- 测试启动时执行 Alembic `upgrade head`，结束时执行 `downgrade base`。
- FastAPI 契约测试加载唯一真实入口 `app.main:app`，不使用 stub。
