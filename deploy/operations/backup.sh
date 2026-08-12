#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-/srv/yoga-sys}"
BACKUP_DIR="${BACKUP_DIR:-/srv/yoga-sys/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
COMPOSE_FILE="${COMPOSE_FILE:-compose.prod.yml}"
DB_SERVICE="${DB_SERVICE:-postgres}"
DB_USER="${DB_USER:-yoga}"
DB_NAME="${DB_NAME:-yoga_sys}"
BACKUP_PREFIX="${BACKUP_PREFIX:-trial}"
STAMP="$(date +%F_%H%M%S)"
BACKUP_FILE="$BACKUP_DIR/${BACKUP_PREFIX}_${DB_NAME}_${STAMP}.dump"

mkdir -p "$BACKUP_DIR"

docker compose -f "$PROJECT_DIR/$COMPOSE_FILE" exec -T "$DB_SERVICE" \
  pg_dump -U "$DB_USER" -Fc "$DB_NAME" \
  > "$BACKUP_FILE"

find "$BACKUP_DIR" -name "${BACKUP_PREFIX}_${DB_NAME}_*.dump" -mtime "+${RETENTION_DAYS}" -delete

echo "backup written: $BACKUP_FILE"
