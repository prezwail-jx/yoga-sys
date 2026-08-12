# Yoga Sys 单域名双环境生产部署手册

本文记录 `124.220.91.149` 单机单域名路径分流的部署。原 `/srv/yoga-sys` 及其 `yoga_sys` 数据库原地保留为 trial；production 在 `/srv/yoga-sys-prod` 创建全新空数据库，不复制测试业务数据。所有流量共用 `https://yoga.tuitukj.com`，不新增子域名。

## 环境映射

| 用途 | trial | production |
|---|---|---|
| Compose / 项目名 | `compose.prod.yml` / `yoga-sys` | `compose.release.yml` / `yoga-sys-prod` |
| 小程序 / API 路径 | `https://yoga.tuitukj.com/backend-trial` | `https://yoga.tuitukj.com/backend` |
| 浏览器网页 | 无独立入口 | `https://yoga.tuitukj.com` |
| PostgreSQL | `yoga / yoga_sys` | `yoga_prod / yoga_sys_prod` |
| 数据卷 | `yoga-sys_postgres-data`（现有） | `yoga-sys-prod_postgres-prod-data`（新建） |
| 备份目录 | `/srv/yoga-sys/backups` | `/srv/yoga-sys-prod/backups` |

本地 develop API 为 `http://127.0.0.1:8000`。同一小程序可共用 AppID/AppSecret，但两环境的数据库密码、JWT secret、identity pepper、source fingerprint pepper 必须完全独立。

## 前置条件

- `yoga.tuitukj.com` A 记录指向 `124.220.91.149`；已有有效证书，无需新增 DNS 或扩展证书。
- 云安全组和 UFW 放行 80/443，PostgreSQL、FastAPI、Nuxt 不发布宿主机端口。
- 新镜像基于已提交 SHA 构建并导入服务器；当前 `20260811` 镜像不包含后续代码，部署前必须重新构建。
- 真实环境文件权限为 `root:root 0600`，不得提交仓库。

## 部署文件

```text
/srv/yoga-sys/                    # trial + edge Nginx/certbot
├── compose.prod.yml
├── env/backend.env
├── env/postgres.env
├── nginx/{bootstrap,production-transition,production,default}.conf
└── operations/

/srv/yoga-sys-prod/               # production，无宿主机端口
├── compose.release.yml
├── env/backend.prod.env
├── env/postgres.prod.env
└── operations/
```

## 首次拆分步骤

### 1. 备份并确认 trial 数据卷

```bash
/srv/yoga-sys/operations/backup.sh
docker volume inspect yoga-sys_postgres-data
docker compose -f /srv/yoga-sys/compose.prod.yml ps
```

禁止执行 `docker compose down -v`，禁止删除或改名现有 `yoga-sys_postgres-data`。

### 2. 创建共享边缘网络并重建 trial

```bash
docker network inspect yoga-edge >/dev/null 2>&1 || docker network create yoga-edge
docker compose -f /srv/yoga-sys/compose.prod.yml config --quiet
docker compose -f /srv/yoga-sys/compose.prod.yml up -d --force-recreate backend frontend nginx
```

现有 Compose 的项目名保持 `yoga-sys`，因此数据库继续挂载原卷。确认 `backend-trial`、`frontend-trial` 可由 Nginx 解析。

### 3. 切换到过渡配置

`production-transition.conf` 中 `/backend` 与 `/backend-trial` 都指向 trial，且不引用尚未启动的 production upstream，因此现有流量不中断：

```bash
cp /srv/yoga-sys/nginx/production-transition.conf /srv/yoga-sys/nginx/default.conf
docker compose -f /srv/yoga-sys/compose.prod.yml exec nginx nginx -t
docker compose -f /srv/yoga-sys/compose.prod.yml restart nginx

curl https://yoga.tuitukj.com/backend/healthz
curl https://yoga.tuitukj.com/backend-trial/healthz
curl https://yoga.tuitukj.com/healthz
```

此阶段三个地址都应返回现有 trial 数据。

### 4. 创建 production 空库

```bash
install -d -m 750 /srv/yoga-sys-prod/env /srv/yoga-sys-prod/backups
cp env/backend.prod.env.example /srv/yoga-sys-prod/env/backend.prod.env
cp env/postgres.prod.env.example /srv/yoga-sys-prod/env/postgres.prod.env
chmod 600 /srv/yoga-sys-prod/env/*.env
```

用 `openssl rand -hex 32` 生成各项 production 密钥，确认 `DATABASE_URL` 使用 `postgres-prod:5432/yoga_sys_prod`，且密码与 `postgres.prod.env` 一致。随后：

```bash
docker compose -f /srv/yoga-sys-prod/compose.release.yml config --quiet
docker compose -f /srv/yoga-sys-prod/compose.release.yml up -d postgres-prod
docker compose -f /srv/yoga-sys-prod/compose.release.yml exec postgres-prod \
  pg_isready -U yoga_prod -d yoga_sys_prod
docker compose -f /srv/yoga-sys-prod/compose.release.yml run --rm backend-prod alembic upgrade head
docker compose -f /srv/yoga-sys-prod/compose.release.yml run --rm backend-prod alembic current
docker compose -f /srv/yoga-sys-prod/compose.release.yml run --rm backend-prod \
  python -m app.scripts.seed_users
docker compose -f /srv/yoga-sys-prod/compose.release.yml up -d
```

seed 后删除 production 环境文件中的 `ADMIN_*`、`COACH_*`。不要向 production 导入 trial 的会员、预约、交易、审计或微信绑定。

### 5. 最终流量切换

先在 `yoga-edge` 内验证 `backend-prod:8000/healthz` 和 `frontend-prod:3000`，再切最终配置：

```bash
docker compose -f /srv/yoga-sys/compose.prod.yml exec nginx \
  wget -qO- http://backend-prod:8000/healthz

cp /srv/yoga-sys/nginx/production.conf /srv/yoga-sys/nginx/default.conf
docker compose -f /srv/yoga-sys/compose.prod.yml exec nginx nginx -t
docker compose -f /srv/yoga-sys/compose.prod.yml restart nginx

curl https://yoga.tuitukj.com/backend/healthz
curl https://yoga.tuitukj.com/backend-trial/healthz
curl https://yoga.tuitukj.com/healthz
```

业务验收必须确认 `/backend` 和主域网页为空白正式数据，`/backend-trial` 仍返回原测试账号和数据。

## 小程序发布

- develop：`http://127.0.0.1:8000`
- trial：`https://yoga.tuitukj.com/backend-trial`，允许密码切换测试账号
- release：`https://yoga.tuitukj.com/backend`，仅微信登录
- 微信 request 合法域名：`https://yoga.tuitukj.com`（不带路径和端口）

先上传 trial 并从服务日志确认请求命中 `backend-trial`，正式小程序只有在主体、类目、隐私、资质和真机门禁完成后发布。

## 升级、备份与回滚

两套环境分别执行迁移和重建，禁止使用同一条未显式标明环境的运维命令。备份脚本参数和恢复核对流程见 `deploy/README.md`、`deploy/operations/restore.md`。

production 切换失败时，将 Nginx 切回 `production-transition.conf` 并验证；该操作让 `/backend` 和主域网页回到 trial，不修改任何数据库。镜像回滚使用上一 tag。微信登录故障可在目标环境设置 `WECHAT_AUTH_ENABLED=false` 后只重启对应 backend，不影响 Nuxt 密码登录。
