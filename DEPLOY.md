# Yoga Sys 生产部署手册

本文档记录 yoga-sys 生产服务器的实际部署步骤与踩坑记录，供上线与升级复用。

## 目标环境

- 服务器：124.220.91.149（x86_64 / amd64），Ubuntu/Debian
- 域名：yoga.tuitukj.com（ICP 已备案，A 记录指向该服务器）
- 交付物：`yoga-sys-release-<日期>-linux-amd64.tar.gz`（离线部署包 + `.sha256` 校验文件）

## 部署包结构

```text
yoga-sys-release-20260811-linux-amd64/
├── compose.prod.yml          # 生产五服务编排
├── README.md
├── release-manifest.txt      # 镜像 ID / Git SHA / 版本说明
├── SHA256SUMS
├── env/                      # 环境变量示例（真实文件在服务器生成，勿提交）
│   ├── backend.env.example
│   └── postgres.env.example
├── nginx/
│   ├── bootstrap.conf        # HTTP 引导（先于证书）
│   └── production.conf       # HTTPS 生产
├── operations/
│   ├── backup.sh             # 数据库备份脚本
│   └── restore.md            # 恢复流程
└── images/
    └── yoga-stack-<日期>-linux-amd64.tar   # 5 个镜像
```

## 一次性上线步骤

### 1. 上传并校验

```bash
scp yoga-sys-release-<日期>-linux-amd64.tar.gz root@124.220.91.149:/root/
scp yoga-sys-release-<日期>-linux-amd64.tar.gz.sha256 root@124.220.91.149:/root/
cd /root && sha256sum -c yoga-sys-release-<日期>-linux-amd64.tar.gz.sha256
```

### 2. 安装 Docker（如未安装）

```bash
sudo apt update
sudo apt install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
. /etc/os-release
printf '%s\n' "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" | sudo tee /etc/apt/sources.list.d/docker.list
sudo apt update && sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
```

### 3. 解压与导入镜像

```bash
sudo mkdir -p /srv/yoga-sys
sudo tar -xzf yoga-sys-release-<日期>-linux-amd64.tar.gz -C /srv/yoga-sys --strip-components=1
cd /srv/yoga-sys
sudo docker load -i images/yoga-stack-<日期>-linux-amd64.tar
docker image ls   # 确认 5 个镜像
```

### 4. 写环境变量（敏感，勿外传）

```bash
sudo cp env/postgres.env.example env/postgres.env
sudo cp env/backend.env.example env/backend.env
sudo chmod 600 env/postgres.env env/backend.env
sudoedit env/postgres.env    # POSTGRES_PASSWORD
sudoedit env/backend.env     # JWT_SECRET / WECHAT_APP_SECRET / 两个 pepper / 数据库密码
```

密钥用 `openssl rand -hex 32` 生成；`JWT_SECRET`、`WECHAT_APP_SECRET`、`WECHAT_IDENTITY_PEPPER`、`WECHAT_SOURCE_FINGERPRINT_PEPPER` 必须互不相同；`DATABASE_URL` 密码与 `postgres.env` 一致。

```bash
sudo tee .env <<'EOF'
YOGA_IMAGE_TAG=<日期>
EOF
docker compose -f compose.prod.yml config --quiet
```

### 5. 起库、迁移、seed（一次性）

```bash
docker compose -f compose.prod.yml up -d postgres
docker compose -f compose.prod.yml exec postgres pg_isready -U yoga -d yoga_sys
docker compose -f compose.prod.yml run --rm backend alembic upgrade head
docker compose -f compose.prod.yml run --rm backend alembic current   # 0008_wechat_identity (head)
docker compose -f compose.prod.yml run --rm backend python -m app.scripts.seed_users
```

seed 后从 `env/backend.env` 删除/注释 `ADMIN_*`、`COACH_*` 四行。

### 6. 启动全套

```bash
sudo cp nginx/bootstrap.conf nginx/default.conf
docker compose -f compose.prod.yml up -d
docker compose -f compose.prod.yml ps
curl -I http://yoga.tuitukj.com   # 200
```

### 7. 签发证书并切 HTTPS

```bash
# 注意：必须 --entrypoint certbot，否则会进入常驻续期循环而"卡住"
docker compose -f compose.prod.yml run --rm --entrypoint certbot certbot certonly \
  --webroot --webroot-path=/var/www/certbot \
  --domain yoga.tuitukj.com --email <你的邮箱> --agree-tos --no-eff-email

sudo cp nginx/production.conf nginx/default.conf
sudo docker compose -f compose.prod.yml exec nginx nginx -t
sudo docker compose -f compose.prod.yml restart nginx
curl https://yoga.tuitukj.com/healthz   # {"status":"ok"}
```

### 8. 防火墙与验证

```bash
sudo ufw allow 22/tcp && sudo ufw allow 80/tcp && sudo ufw allow 443/tcp
sudo ufw --force enable
```

云安全组需放行入方向 80/443。浏览器登录 `https://yoga.tuitukj.com/login` 完成业务验证。

## 本次踩坑记录

1. **系统自带 nginx 占用 80/443**：`ss -tlnp` 确认后执行 `sudo systemctl stop nginx && sudo systemctl disable nginx`（disable 防止重启后抢端口）。
2. **nginx 容器 `host not found in upstream "backend"`**：容器未 join `internal` 网络，用 `docker compose up -d --force-recreate nginx` 强制重建解决。
3. **`docker compose run certbot certonly` 卡住**：compose 服务的 entrypoint 是常驻 renew 循环，`run` 不覆盖 entrypoint；必须加 `--entrypoint certbot`。
4. **镜像 tag 与 Git 对齐**：镜像构建必须基于已提交的 SHA；本机曾因 `latest` 镜像过期导致 compose 失效，改指日期 tag。

## 升级流程

```bash
# 1. 上传并校验新包 → 解压 → docker load
# 2. 迁移（新版本有迁移时）
docker compose -f compose.prod.yml run --rm backend alembic upgrade head
# 3. 更新 .env 的 YOGA_IMAGE_TAG 或 compose 镜像 tag
# 4. 重启服务
docker compose -f compose.prod.yml up -d backend frontend nginx
docker compose -f compose.prod.yml ps
# 5. 验证通过后清理旧镜像
docker image prune
```

## 回滚与备份

- **备份**：`/usr/local/bin/yoga-backup`（`operations/backup.sh` 安装），输出到 `/srv/yoga-sys/backups/`，配每日 cron 保留 30 天。
- **恢复**：见 `operations/restore.md`，恢复前先停 backend。
- **微信登录故障回滚**：`env/backend.env` 设 `WECHAT_AUTH_ENABLED=false` 并重启 backend，不影响网页密码登录。
- **代码回滚**：`docker load` 上一版本 tar，换回旧 `YOGA_IMAGE_TAG` 后 `up -d`。

## 小程序发布

- 客户端 API 基址：`miniapp/miniprogram/config/environment.ts`，trial/release 为 `https://yoga.tuitukj.com/backend`。
- 微信后台 request 合法域名：`https://yoga.tuitukj.com`（只填域名，不带路径/端口）。
- 证书续期：`yoga-sys-certbot-1` 常驻容器每 12 小时 `renew`；可用 `docker compose run --rm --entrypoint certbot certbot renew --dry-run` 验证。
