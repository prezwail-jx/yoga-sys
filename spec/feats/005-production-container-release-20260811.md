# 生产容器发布与离线打包

**时间**: 2026-08-11

## 变更点

1. 新增 `frontend/Dockerfile` 与 `frontend/.dockerignore`，Node 20 多阶段构建并仅保留 Nitro 产物。
2. 修改 `backend/Dockerfile`，启动命令不再自动执行迁移和 seed；只运行 Uvicorn。
3. 修改 `backend/app/scripts/seed_users.py`：生产环境要求显式强密码、拒绝默认密码、已存在账号不可覆盖；seed 改为一次性运维命令。
4. 修改 `miniapp/miniprogram/config/environment.ts`：trial/release API 基址改为 `https://yoga.tuitukj.com/backend`，避免与 Nuxt 页面同名路由冲突。
5. 新增 `deploy/compose.prod.yml`：postgres、backend、frontend、nginx、certbot 五服务，仅发布 80/443，数据卷持久化，健康检查与依赖顺序。
6. 新增 `deploy/nginx/bootstrap.conf`（HTTP 引导）与 `deploy/nginx/production.conf`（TLS），含微信认证限流与 `/backend` 前缀转发。
7. 新增 `deploy/env/*.env.example`、`deploy/operations/backup.sh`、`deploy/operations/restore.md`、`deploy/README.md`。
8. 更新 `.gitignore`，保护 `deploy/env/*.env` 与生成的 `nginx/default.conf`。

## 测试计划

- `docker compose -f deploy/compose.prod.yml config --quiet`。
- 后端：`uv run pytest -q`、`uv run ruff check app tests`、`uv run mypy`。
- 前端：`npm run lint`、`npm run typecheck`、`npm run test`、`npm run build`。
- 小程序：`npm run lint`、`npm run typecheck`、`npm test`、`npm run build`。
- 构建 `linux/amd64` 的 backend/frontend 镜像并检查 Cmd、架构、标签。
- 固定 certbot `v5.7.0`、postgres:16、nginx:alpine 基础镜像。
- 生成 `docker save` 离线包与 `SHA256SUMS`。

## 假设与风险

- 目标服务器为 x86_64、全新数据库、完全离线 `docker load`。
- 真实 secret 只写入服务器 `/srv/yoga-sys/env/*.env`，绝不进入部署包。
- certbot 镜像以 `v5.7.0` 固定，若 Docker Hub 拉取失败则暂停并沟通。
- 迁移与 seed 由运维命令执行，普通 `up -d` 不触碰数据库。

## 结果总结

- 新增前端多阶段 Dockerfile（node:24-slim，固定 npm@11.6.2 以匹配 lockfile，保证 `npm ci` 可复现）。
- 后端镜像启动只运行 uvicorn，不再自动迁移/seed；seed 增加生产守卫。
- 小程序 trial/release API 基址改为 `https://yoga.tuitukj.com/backend`。
- 新增 compose.prod.yml、Nginx bootstrap/production 配置、env 示例、备份与恢复脚本、部署 README。
- 提交 `b2f8d8b`（生产部署栈）与 `dd9c832`（前端构建修复）已双平台推送。
- 应用镜像 `yoga-sys-backend:dd9c832`、`yoga-sys-frontend:dd9c832` 构建并冒烟通过；基础镜像 postgres:16、nginx:alpine、certbot/certbot:v5.7.0 固定 amd64。
- 离线包：`dist/yoga-sys-release-dd9c832-linux-amd64.tar.gz`（513M）与校验文件已生成并验证。

## 后续跟进

- 服务器安装 Docker、`docker load`、写入 `/srv/yoga-sys/env/*.env`、`alembic upgrade head`、一次性 seed、certbot 签发证书。
- 微信后台添加合法域名 `https://yoga.tuitukj.com`，真机验收后进入提审。
