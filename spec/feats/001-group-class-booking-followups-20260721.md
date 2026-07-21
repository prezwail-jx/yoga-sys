# 团课预约后续问题记录

日期：2026-07-21 10:58:43 +0800

来源：`group-class-booking-loop` 归档前验证报告

状态：待处理

## 问题清单

1. 会员角色的团课基础资料权限缺少精确测试。现有测试主要使用教练角色，尚未直接验证会员可以读取启用的课程、教室和教练资料，以及会员写入时返回 `403` 并记录拒绝审计。
2. 已有预约历史的课次修改关键字段缺少精确测试。实现会拒绝修改课程、教练、教室或起止时间，但现有测试只覆盖终态课次修改。
3. 同一会员预约不同但时间重叠课次缺少集成测试。需要确认第二次预约返回 `409`，且不创建预约或 `reserve_hold` 事件。
4. 真实预约完成后的核销时间线缺少完整断言。需要分别确认签到和缺勤链路包含 `reserve_hold` 及唯一终态，并共享同一个业务引用。
5. 跨会员预约操作缺少精确测试。需要确认会员不能查询或取消其他会员的预约，拒绝后预约状态不变并记录审计。
6. 停卡和到期会员的组合场景缺少测试。需要确认这两类会员可以登录查看本人资料，但预约时返回 `409` 且不预扣权益。
7. 预约业务校验失败的审计范围不足。容量不足、窗口关闭、时间冲突等 `409` 以及关键 `422` 目前不会统一记录 `result=rejected`、失败原因和 trace ID。

## 关联位置

- `backend/app/api/middleware/audit_rejections.py`
- `backend/app/services/class_scheduling.py`
- `backend/app/services/class_booking.py`
- `backend/tests/integration/test_class_catalog_scheduling.py`
- `backend/tests/integration/test_account_booking_loop.py`
- `backend/tests/integration/test_us3_exception_cross_member_access.py`
- `backend/tests/integration/test_us1_boundary_member_status.py`
