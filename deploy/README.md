# Yoga Sys Production Deployment

Offline single-host deployment using `docker save`/`docker load`.

## Bundle Layout

```text
yoga-sys-release-<SHA>-linux-amd64/
├── compose.prod.yml
├── README.md
├── release-manifest.txt
├── SHA256SUMS
├── env/
│   ├── backend.env.example
│   └── postgres.env.example
├── nginx/
│   ├── bootstrap.conf
│   └── production.conf
├── operations/
│   ├── backup.sh
│   └── restore.md
└── images/
    └── yoga-stack-<SHA>-linux-amd64.tar
```

## Prerequisites

- Ubuntu/Debian x86_64 server with Docker Engine and the Compose plugin.
- Ports `80` and `443` reachable from the internet.
- DNS `yoga.tuitukj.com` pointing to the server.
- An email address for Let's Encrypt notifications.

## 1. Load Images

```bash
sudo docker load -i images/yoga-stack-<SHA>-linux-amd64.tar
sudo docker image ls
```

Confirm `postgres:16`, `nginx:alpine`, `certbot/certbot:<version>`,
`yoga-sys-backend:<SHA>` and `yoga-sys-frontend:<SHA>` are present.

## 2. Write Secrets

```bash
sudo install -d -m 750 /srv/yoga-sys
sudo cp -r env nginx compose.prod.yml operations /srv/yoga-sys/
sudo cp nginx/bootstrap.conf /srv/yoga-sys/nginx/default.conf
```

Create real env files (never commit these):

```bash
sudo install -m 600 /dev/null /srv/yoga-sys/env/postgres.env
sudo install -m 600 /dev/null /srv/yoga-sys/env/backend.env
sudoedit /srv/yoga-sys/env/postgres.env
sudoedit /srv/yoga-sys/env/backend.env
```

Generate secrets with `openssl rand -hex 32`. `JWT_SECRET`,
`WECHAT_APP_SECRET`, `WECHAT_IDENTITY_PEPPER` and
`WECHAT_SOURCE_FINGERPRINT_PEPPER` must all differ.

## 3. Start Database

```bash
cd /srv/yoga-sys
docker compose -f compose.prod.yml config --quiet
docker compose -f compose.prod.yml up -d postgres
docker compose -f compose.prod.yml exec postgres pg_isready -U yoga -d yoga_sys
```

## 4. Migrate and Seed (one-time)

```bash
docker compose -f compose.prod.yml run --rm \
  backend alembic upgrade head

docker compose -f compose.prod.yml run --rm \
  backend alembic current            # expect 0008_wechat_identity (head)

docker compose -f compose.prod.yml run --rm \
  backend python -m app.scripts.seed_users
```

After seeding, remove `ADMIN_USERNAME/ADMIN_PASSWORD/COACH_USERNAME/
COACH_PASSWORD` from `env/backend.env`. The backend image never runs
migrations or seeding on startup.

## 5. Start the Stack

```bash
export YOGA_IMAGE_TAG=<SHA>
docker compose -f compose.prod.yml up -d
docker compose -f compose.prod.yml ps
docker compose -f compose.prod.yml logs --tail=100 backend
docker compose -f compose.prod.yml logs --tail=100 frontend
```

## 6. Issue TLS Certificate

`nginx/default.conf` currently uses the HTTP bootstrap config. Confirm HTTP:

```bash
curl -I http://yoga.tuitukj.com
```

Issue the certificate:

```bash
docker compose -f compose.prod.yml run --rm certbot certonly \
  --webroot --webroot-path=/var/www/certbot \
  --domain yoga.tuitukj.com --email <admin@example.com> \
  --agree-tos --no-eff-email
```

Then switch to HTTPS:

```bash
cp /srv/yoga-sys/nginx/production.conf /srv/yoga-sys/nginx/default.conf
docker compose -f compose.prod.yml exec nginx nginx -t
docker compose -f compose.prod.yml restart nginx
```

## 7. Renew Certificates

The `certbot` service renews every 12 hours. Verify manually:

```bash
docker compose -f compose.prod.yml run --rm certbot renew --dry-run
```

## 8. Firewall

```bash
sudo ufw default deny incoming
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable
```

Only `80` and `443` are published by Compose. PostgreSQL, FastAPI and Nuxt
remain on the internal network.

## 9. Backups

```bash
chmod +x /srv/yoga-sys/operations/backup.sh
/srv/yoga-sys/operations/backup.sh
```

Add a daily cron job (adjust paths), then perform one restore drill.

## 10. WeChat Console

After HTTPS is live, add the request legal domain in the Mini Program console:

```text
https://yoga.tuitukj.com
```

The Mini Program release/trial API base is:

```text
https://yoga.tuitukj.com/backend
```

Verify on real iOS and Android devices: first-time binding, returning login,
unbind/rebind, token-expiry recovery, member and coach flows.

## 11. Verify and Rollback

```bash
curl https://yoga.tuitukj.com/healthz
curl -I https://yoga.tuitukj.com/login
```

Rollback paths:

- **Code**: `docker load` the previous `yoga-stack-<old-SHA>.tar`, set
  `YOGA_IMAGE_TAG=<old-SHA>`, run `docker compose -f compose.prod.yml up -d`.
- **WeChat login issue**: set `WECHAT_AUTH_ENABLED=false` in `env/backend.env`
  and restart backend. Nuxt password login remains available.
- **Data**: restore from a verified backup (see `operations/restore.md`).

## Image Builds (development machine)

```bash
docker buildx build --platform linux/amd64 --load -t yoga-sys-backend:<SHA> backend
docker buildx build --platform linux/amd64 --load -t yoga-sys-frontend:<SHA> frontend
docker save yoga-sys-backend:<SHA> yoga-sys-frontend:<SHA> postgres:16 \
  nginx:alpine certbot/certbot:<version> \
  -o dist/images/yoga-stack-<SHA>-linux-amd64.tar
```
