#!/usr/bin/env bash
# PostgreSQL backup script for HRMS.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ENV_FILE:-$SCRIPT_DIR/../backend/.env}"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source <(grep -v '^\s*#' "$ENV_FILE" | sed 's/\r$//')
  set +a
fi

DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER:-postgres}"
DB_NAME="${DB_NAME:-hrms_db}"
BACKUP_DIR="${BACKUP_DIR:-$SCRIPT_DIR/../backups}"
STAMP="$(date +%Y%m%d_%H%M%S)"
OUTFILE="$BACKUP_DIR/hrms_${DB_NAME}_${STAMP}.dump"

mkdir -p "$BACKUP_DIR"
export PGPASSWORD="${DB_PASSWORD:-}"

pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -Fc -f "$OUTFILE"
echo "Backup written to $OUTFILE"
