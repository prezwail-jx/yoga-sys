#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-/srv/yoga-sys}"
BACKUP_DIR="${BACKUP_DIR:-/srv/yoga-sys/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
DB_USER="${DB_USER:-yoga}"
DB_NAME="${DB_NAME:-yoga_sys}"
STAMP="$(date +%F_%H%M%S)"

mkdir -p "$BACKUP_DIR"

docker compose -f "$PROJECT_DIR/compose.prod.yml" exec -T postgres \
  pg_dump -U "$DB_USER" -Fc "$DB_NAME" \
  > "$BACKUP_DIR/yoga_sys_${STAMP}.dump"

find "$BACKUP_DIR" -name '*.dump' -mtime "+${RETENTION_DAYS}" -delete

echo "backup written: $BACKUP_DIR/yoga_sys_${STAMP}.dump"
