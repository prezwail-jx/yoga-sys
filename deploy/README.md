# Yoga Sys Single-Domain Dual-Environment Deployment

同一服务器运行相互隔离的 trial 和 production 数据栈，共用 `https://yoga.tuitukj.com`，由现有 trial 栈中的 Nginx 统一发布 80/443。

## 拓扑

| 环境 | Compose | 服务器目录 | API 路径 | 浏览器网页 | 数据库 |
|---|---|---|---|---|---|
| trial | `compose.prod.yml` (`yoga-sys`) | `/srv/yoga-sys` | `/backend-trial` | 无独立入口 | `yoga_sys`，保留现有卷 |
| production | `compose.release.yml` (`yoga-sys-prod`) | `/srv/yoga-sys-prod` | `/backend` | `yoga.tuitukj.com` | `yoga_sys_prod`，新空卷 |

两套 backend/frontend 通过预创建的外部网络 `yoga-edge` 与边缘 Nginx 通信。PostgreSQL 只加入各自内部网络，production Compose 不发布任何宿主机端口。不新增任何子域名。

## 文件和密钥

trial 使用 `env/backend.env`、`env/postgres.env`；production 使用 `env/backend.prod.env`、`env/postgres.prod.env`。从对应 `.example` 创建真实文件并设为 `0600`。两套环境的数据库密码、`JWT_SECRET`、identity pepper 和 source fingerprint pepper 必须独立；AppID/AppSecret 可属于同一小程序。

```bash
docker network inspect yoga-edge >/dev/null 2>&1 || docker network create yoga-edge
install -m 600 env/backend.prod.env.example env/backend.prod.env
install -m 600 env/postgres.prod.env.example env/postgres.prod.env
```

production 目录需包含 `compose.release.yml`、`env/`，并与 trial 使用相同的 `YOGA_IMAGE_TAG` 或经验证的独立 tag。

## 安全迁移顺序

1. 备份现有 `yoga_sys`；不得执行 `down -v` 或删除 `yoga-sys_postgres-data`。
2. 创建 `yoga-edge`，更新并重建现有 trial 的 backend、frontend、nginx 网络连接。
3. 切换到 `nginx/production-transition.conf`。此时 `/backend` 与 `/backend-trial` 都仍指向 trial，现有客户端不中断。
4. 在 `/srv/yoga-sys-prod` 启动全新的 `postgres-prod`，迁移并 seed；不得导入 trial 数据。
5. 启动 `backend-prod` 和 `frontend-prod`，从 `yoga-edge` 内验证健康状态。
6. 切换到 `nginx/production.conf`，正式 `/backend` 和主域网页才转向 production。
7. 上传 trial 小程序，确认它请求 `/backend-trial`；release 继续请求 `/backend`。

```bash
# trial 网络更新
docker compose -f /srv/yoga-sys/compose.prod.yml up -d --force-recreate backend frontend nginx

# production 首次启动
docker compose -f /srv/yoga-sys-prod/compose.release.yml config --quiet
docker compose -f /srv/yoga-sys-prod/compose.release.yml up -d postgres-prod
docker compose -f /srv/yoga-sys-prod/compose.release.yml run --rm backend-prod alembic upgrade head
docker compose -f /srv/yoga-sys-prod/compose.release.yml run --rm backend-prod python -m app.scripts.seed_users
docker compose -f /srv/yoga-sys-prod/compose.release.yml up -d
```

seed 后删除 production 环境文件中的 `ADMIN_*`、`COACH_*`。切换 Nginx 配置前始终执行：

```bash
cp nginx/<target>.conf nginx/default.conf
docker compose -f compose.prod.yml exec nginx nginx -t
docker compose -f compose.prod.yml restart nginx
```

## 验证与回滚

```bash
curl https://yoga.tuitukj.com/backend/healthz
curl https://yoga.tuitukj.com/backend-trial/healthz
curl https://yoga.tuitukj.com/healthz
```

若 production 验证失败，将 Nginx 切回 `production-transition.conf`，即可让 `/backend` 和主域网页回到 trial；不要回滚或删除数据库卷。代码回滚使用上一镜像 tag，数据恢复见 `operations/restore.md`。

## 备份

```bash
# trial 默认值
/srv/yoga-sys/operations/backup.sh

# production 显式值
PROJECT_DIR=/srv/yoga-sys-prod BACKUP_DIR=/srv/yoga-sys-prod/backups \
COMPOSE_FILE=compose.release.yml DB_SERVICE=postgres-prod DB_USER=yoga_prod \
DB_NAME=yoga_sys_prod BACKUP_PREFIX=prod \
/srv/yoga-sys-prod/operations/backup.sh
```

两套环境使用独立备份目录和 cron。微信 request 合法域名仍只需 `https://yoga.tuitukj.com`，路径由小程序环境配置选择。
