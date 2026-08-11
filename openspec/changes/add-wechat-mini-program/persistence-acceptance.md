# 第二大项验收记录 - WeChat identity persistence

**日期**: 2026-08-05  
**基线 Git SHA**: `5d6f86b`  
**分支**: `002-member-card-core`

## 强模型审查

- `pg_advisory_xact_lock` 在 PostgreSQL 中跨连接生效；此前失败是测试把线程 Session 绑定到同一个外层事务 Connection，导致锁在同一事务内可重入。
- 并发测试现使用 `Session(db_engine)` 创建独立连接，并预先提交账号和 challenge 场景。
- challenge 在绑定前通过 `SELECT FOR UPDATE` 锁定，并检查不存在、已消费、过期和失败次数上限。
- identity 和 account advisory lock 按稳定排序获取，降低死锁风险。
- `(appid, openid_digest)` 和 `(appid, account_id)` 使用命名唯一约束；`IntegrityError` 作为最终防线映射为确定性业务冲突。
- 绑定演员、角色、时间和来源指纹改为必填，并增加外键、角色、摘要长度和有效期约束。
- 清理会删除所有到期 challenge，包括已消费记录。
- 错误凭据计数只有在请求事务正常提交时才会保留；第 3 大项必须返回普通失败结果，不能让 `HTTPException` 触发整个事务回滚。

## PostgreSQL 集成测试

```bash
TEST_DATABASE_URL="<dedicated test database>" uv run pytest -q \
  tests/integration/test_wechat_identity.py
```

结果：`12 passed`。

并发子集连续执行 5 轮，每轮 3 项，共 15 次全部通过。

覆盖范围：

- challenge 创建、查询、消费、过期、失败次数和清理
- 同一映射幂等绑定、身份冲突、账号冲突和 AppID 隔离
- 管理员解绑后的标准重新绑定
- 原始 OpenID、ticket 和 `session_key` 不进入表结构
- 摘要、来源指纹和绑定角色约束
- 两个 OpenID 竞争同一账号
- 同一 OpenID 竞争两个账号
- 同一 ticket 并发消费
- 失败次数在提交后可被新事务读取

## 迁移验证

执行 `0008 -> 0007 -> 0008`：

| 阶段 | Alembic 版本 | `admin_user` 数量 | 数据指纹 |
|---|---|---:|---|
| 降级前 | `0008_wechat_identity` | 3 | `bc6828c39b04fd65503c62b1a789a0d4` |
| 降级后 | `0007_private_training_reporting` | 3 | `bc6828c39b04fd65503c62b1a789a0d4` |
| 再升级 | `0008_wechat_identity` | 3 | `bc6828c39b04fd65503c62b1a789a0d4` |

降级后两张微信表不存在，再升级后恢复；现有账号、会员/教练关联字段未变化。

验收后已清理并发场景创建的测试账号、会员、identity 和 challenge；重复运行集成测试后残留测试账号数为 0。

## 回归结果

- 第二大项修正前，排除历史合约路径测试为 `109 passed, 1 skipped`，覆盖率 85%。
- 权威合约迁移到 `specs/contracts/group-class-booking.openapi.yaml` 后，8 项 contract 测试全部通过。
- 最终完整后端套件：`117 passed, 1 skipped`。

## 结论

第二大项持久化、约束、重放防护和真实独立连接并发测试通过，可以进入第 3 大项。此前 3 个并发失败属于测试连接模型错误，现已纠正，不是 PostgreSQL 事务级 advisory lock 缺陷。
