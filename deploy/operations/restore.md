# Database Restore Procedure

恢复会覆盖目标环境数据。执行前必须同时核对 Compose 文件、数据库服务和数据库名，先做一份新备份，禁止对另一环境执行命令。

## 环境矩阵

| 环境 | 目录 | Compose 文件 | 数据库服务 | 用户 / 数据库 | 备份目录 |
|---|---|---|---|---|---|
| trial | `/srv/yoga-sys` | `compose.prod.yml` | `postgres` | `yoga / yoga_sys` | `/srv/yoga-sys/backups` |
| production | `/srv/yoga-sys-prod` | `compose.release.yml` | `postgres-prod` | `yoga_prod / yoga_sys_prod` | `/srv/yoga-sys-prod/backups` |

下列示例先设置目标环境变量。production 恢复时必须改成矩阵中的 production 值：

```bash
PROJECT_DIR=/srv/yoga-sys
COMPOSE_FILE=compose.prod.yml
BACKEND_SERVICE=backend
DB_SERVICE=postgres
DB_USER=yoga
DB_NAME=yoga_sys
BACKUP_FILE=/srv/yoga-sys/backups/trial_yoga_sys_<STAMP>.dump
```

## 恢复步骤

1. 核对目标容器和数据库。输出必须与上面的目标环境完全一致：

```bash
docker compose -f "$PROJECT_DIR/$COMPOSE_FILE" ps
docker compose -f "$PROJECT_DIR/$COMPOSE_FILE" exec -T "$DB_SERVICE" \
  psql -U "$DB_USER" -d "$DB_NAME" -Atc 'select current_database(), current_user;'
```

2. 使用 `operations/backup.sh` 对目标环境做恢复前备份，然后停止写入：

```bash
docker compose -f "$PROJECT_DIR/$COMPOSE_FILE" stop "$BACKEND_SERVICE"
test -s "$BACKUP_FILE"
```

3. 恢复并按当前镜像执行迁移：

```bash
docker compose -f "$PROJECT_DIR/$COMPOSE_FILE" exec -T "$DB_SERVICE" \
  pg_restore -U "$DB_USER" -d "$DB_NAME" --clean --if-exists \
  < "$BACKUP_FILE"
docker compose -f "$PROJECT_DIR/$COMPOSE_FILE" run --rm "$BACKEND_SERVICE" \
  alembic upgrade head
```

4. 启动并验证对应环境：

```bash
docker compose -f "$PROJECT_DIR/$COMPOSE_FILE" start "$BACKEND_SERVICE"
docker compose -f "$PROJECT_DIR/$COMPOSE_FILE" ps
```

trial 验证 `https://trial.yoga.tuitukj.com/healthz` 和 `https://yoga.tuitukj.com/backend-trial/healthz`；production 验证 `https://yoga.tuitukj.com/healthz` 和 `https://yoga.tuitukj.com/backend/healthz`。

## 安全约束

- trial 备份不得恢复到 production，反之亦然，除非有明确的数据迁移审批。
- production 初始数据库必须为空，不复制 trial 的会员、预约、交易、审计或微信绑定。
- 不执行 `docker compose down -v`，不删除 `yoga-sys_postgres-data` 或 `yoga-sys-prod_postgres-prod-data`。
- 备份文件需限制权限，并定期做隔离环境恢复演练。
