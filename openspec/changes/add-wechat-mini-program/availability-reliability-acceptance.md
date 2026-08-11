# 第六大项验收记录 - Coach availability API reliability

**日期**: 2026-08-07

## 审查与修正

- 教练只能创建、更新和取消自己的私教时段；跨教练操作返回 403。
- 创建、更新和周生成都会确认教练仍处于启用状态。
- 单时段创建和更新拒绝过去时间；周生成保留未来日期的成功结果，并以 `private_slot_in_past` 返回过去日期冲突。
- 私教时段重叠返回 `private_slot_time_conflict`，与有效团课重叠返回 `coach_class_time_conflict`。
- 锁定时段及存在 pending/confirmed 预约的时段不可取消。
- 活跃预约检查改为按时段 ID 查询 pending/confirmed 预约，不再依赖教练预约列表的首条记录。

## 幂等与兼容性

- `POST /private-slots`、`PATCH /private-slots/{slotId}` 和 `DELETE /private-slots/{slotId}` 接受可选 `Idempotency-Key`。
- 提供 key 时，同一 actor、scope、key 和 payload 重放原状态码与响应体；同 key 不同 payload 返回 409。
- 不提供 key 时直接执行原有业务路径，现有 Nuxt BFF 调用保持兼容。
- `POST /private-slots/generate-week` 继续强制要求 `Idempotency-Key`，并返回 `created` 和 `conflicts`。

## PostgreSQL 集成测试

```bash
TEST_DATABASE_URL="postgresql+psycopg://yoga:yoga123@localhost:5432/yoga_sys_test" \
  uv run pytest tests/integration/test_private_slot_reliability.py
```

结果：`5 passed`。

覆盖范围：

- 单时段创建、更新和取消的成功重放
- 同 key 不同 payload 冲突
- 模拟响应丢失后的同 key 重试
- 不携带 key 的浏览器兼容调用
- 跨教练创建、更新和取消
- pending 预约锁定时段及取消保护
- 停用教练、过去时间、私教重叠和团课冲突
- 周生成必需 key、过去日期冲突、时段冲突、部分成功和重放

## 其他校验

- 私教服务单元测试：`8 passed`。
- OpenAPI 与团课合约测试：`15 passed`。
- Python 编译检查通过。
- 完整后端套件结果为 `247 passed, 1 skipped, 1 failed`；唯一失败是既有会员卡测试将 `TODAY` 固定为 `2026-08-06`，运行日为 `2026-08-07`，与本大项改动无关，留待 10.3 回归门处理。

## 结论

第六大项的教练可用时段规则、移动网络重试幂等性和 Nuxt 兼容性已完成，可进入原生小程序基础建设。
