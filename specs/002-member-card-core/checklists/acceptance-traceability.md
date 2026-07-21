# 验收追踪矩阵

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
| 管理员查看会员交易与核销时间线 | US3-AS1、FR-007/009 | T046、T054、T056、T057 | `test_admin_replays_purchase_reserve_and_checkin_chain_from_timeline` |
| 预扣、签到、取消与缺勤链路可关联 | US3-AS2、FR-006/010、CA-002/003/004 | T046、T050-T055、T058 | `test_admin_replays_purchase_reserve_and_checkin_chain_from_timeline`、`test_terminal_events_are_mutually_exclusive` |
| 同日多事件稳定排序且不丢失 | US3-AS3、FR-007 | T047、T051、T054 | `test_same_day_cancel_rebook_and_absence_are_stably_ordered` |
| 会员跨会员读取被拒绝并审计 | US3-AS4、FR-008/009、CA-001/004 | T048、T054、T056 | `test_member_can_read_self_but_not_another_member_and_denial_is_audited` |

## 团课预约闭环

| 验收场景 | OpenSpec Requirement | 任务 | 自动化证据 |
|---|---|---|---|
| 基础资料权限、唯一性和有效引用 | class-catalog | 2.1、2.2、6.1 | `test_class_catalog_scheduling.py::test_catalog_permissions_and_case_insensitive_uniqueness`、`test_session_rejects_disabled_resources_room_overcapacity_and_terminal_updates` |
| 指定课程卡保存校验与预约适用范围 | class-catalog、class-booking-writeoff | 6.7 | `test_card_product_service.py`、`test_specific_course_card_validates_course_ids_on_create_and_update`、`test_booking_checkin_absence_and_venue_force_refund` |
| 周课表、资源冲突、生命周期和复制周 | class-scheduling | 2.3、2.4、6.1 | `test_class_catalog_scheduling.py::test_schedule_conflicts_lifecycle_visibility_and_copy`、`test_completed_session_requires_end_time` |
| 会员和教练账号唯一绑定及资源令牌 | member-account-binding | 3.1–3.3 | `test_account_binding_auth.py`、`test_account_booking_loop.py::test_admin_creates_member_and_coach_resource_scoped_accounts` |
| 预约、取消、签到、缺勤和馆方强制返还 | class-booking-writeoff | 4.1–4.5、6.1、6.7 | `test_account_booking_loop.py::test_booking_checkin_absence_and_venue_force_refund`、`test_member_cancel_cutoff_replay_terminal_exclusion_and_rebook` |
| 最后名额、重复预约和终态互斥 | class-booking-writeoff | 6.2 | `test_class_booking_concurrency.py` |
| 目标数据量及写入/时间线 p95 记录 | performance goal | 6.4 | `test_group_class_performance.py::test_group_class_target_volume_and_p95_records` |
| 管理员和会员前端流程 | class-scheduling、class-booking-writeoff | 5.1–5.5、6.3 | `group-class.spec.ts::会员可以从真实周课表预约并在我的预约中取消`、`group-class.spec.ts::管理员可以为会员开通资源绑定账号` |
| 教练角色课表与导航隔离 | class-scheduling、member-account-binding | 5.5、6.3 | `us1.spec.ts::教练登录后进入本人课表` |
| 会员预约窗口和取消截止前端规则 | class-booking-writeoff | 5.4、6.3 | `classBooking.spec.ts` |

## 验收环境

- PostgreSQL 16 容器。
- 测试启动时执行 Alembic `upgrade head`，结束时执行 `downgrade base`。
- FastAPI 契约测试加载唯一真实入口 `app.main:app`，不使用 stub。
