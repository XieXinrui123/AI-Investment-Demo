#!/bin/bash
# Restore the local SQLite database from a backup file.

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DB_FILE="$PROJECT_ROOT/backend/ai_berkshire.db"

if [ -z "$1" ]; then
    echo "Usage: ./scripts/restore_db.sh backups/ai_berkshire-YYYYMMDD-HHMMSS.db"
    exit 1
fi

BACKUP_FILE="$PROJECT_ROOT/$1"
if [ ! -f "$BACKUP_FILE" ]; then
    BACKUP_FILE="$1"
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Backup file not found: $1"
    exit 1
fi

if [ -f "$DB_FILE" ]; then
    safety_copy="$DB_FILE.before-restore-$(date +%Y%m%d-%H%M%S)"
    cp "$DB_FILE" "$safety_copy"
    echo "Current database saved to: $safety_copy"
fi

cp "$BACKUP_FILE" "$DB_FILE"
echo "Database restored from: $BACKUP_FILE"
