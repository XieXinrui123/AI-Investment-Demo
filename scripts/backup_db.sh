#!/bin/bash
# Back up the local SQLite database for personal data safety.

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DB_FILE="$PROJECT_ROOT/backend/ai_berkshire.db"
BACKUP_DIR="$PROJECT_ROOT/backups"

if [ ! -f "$DB_FILE" ]; then
    echo "Database not found: $DB_FILE"
    exit 1
fi

mkdir -p "$BACKUP_DIR"
timestamp="$(date +%Y%m%d-%H%M%S)"
backup_file="$BACKUP_DIR/ai_berkshire-$timestamp.db"

cp "$DB_FILE" "$backup_file"
echo "Backup created: $backup_file"
