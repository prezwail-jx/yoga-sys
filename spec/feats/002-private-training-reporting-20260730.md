# 私教闭环与真实报表落地计划

日期：2026-07-30

来源：OpenSpec change `complete-p0-private-training-and-reporting`

状态：已完成实现，存在历史 contract fixture 阻塞项

## 变更点

1. 将私教预约从 Mock 页面升级为真实后端闭环，覆盖教练空闲时段、会员预约、待确认取消、教练确认/拒绝、签到和课时记录。
2. 私教确认时每次扣 1 次私教卡，签到时记录完成；消耗课时仅用于统计。
3. 私教与团课双向阻止会员预约和教练排班时间重叠。
4. 将统计报表从 Mock 数据升级为真实聚合，覆盖会员、卡项、财务、团课和私教指标。
5. 增加报表日期和维度筛选、趋势、明细下钻和 180 天内同步 Excel 导出。
6. 替换前端 BFF Mock 路由，移除私教和报表导航 Mock 标记。

## 测试计划

1. 后端单元与集成测试覆盖私教时段冲突、并发预约、权限边界、确认扣次、拒绝/取消释放时段、签到记录和时间线。
2. 后端报表测试覆盖汇总、筛选、趋势、明细对账、退款金额符号、Excel 内容和 180 天限制。
3. 前端单元测试覆盖私教角色化 UI、报表格式化、筛选和下载交互。
4. E2E 覆盖会员预约/取消、教练确认/签到、管理员报表筛选/下钻/导出触发。
5. 执行 `uv run pytest`、`npm run lint`、`npm run typecheck`、`npm run test:unit`、`npm run build`，条件允许时执行 `npm run test:e2e`。

## 假设与风险

1. 现有 `WriteOffEvent` 使用 `reserve_hold -> checkin_commit` 可复用到私教，不新增核销事件类型。
2. Excel 使用同步生成，超过 180 天返回业务错误；未来如数据量增大再引入异步导出。
3. 当前分支为 `002-member-card-core`，本次按用户确认继续在当前分支实施，不创建新分支。
4. 工作区已有 `README.md` 端口修改会保留，不回退。

## 结果总结

1. 新增私教数据模型、迁移、服务、路由和 Nuxt BFF，页面已从 Mock 切到真实后端。
2. 私教支持教练/管理员发布时段、周批量生成、会员预约、确认、拒绝、待确认取消、签到和课时记录。
3. 确认时复用 `reserve_hold` 并按私教卡 FEFO 扣 1 次；签到复用 `checkin_commit`，课时数仅用于报表。
4. 团课与私教已在会员预约和教练排班两个方向做时间重叠拦截。
5. 新增真实报表汇总、趋势、明细下钻和 180 天内同步 `.xlsx` 导出，报表接口限定管理员访问。
6. README、features 和导航状态已更新，私教与报表不再标记 Mock。

## 后续跟进

1. `uv run pytest tests/contract -q` 仍受历史文件缺失阻塞：`openspec/changes/group-class-booking-loop/contracts/group-class-booking.openapi.yaml` 不存在。
2. 全量后端 `uv run pytest` 此前 120 秒超时，建议在修复历史 contract fixture 后重新跑完整套件。
3. 如导出数据量增长，再将同步 Excel 导出升级为异步任务。
