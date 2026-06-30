#!/bin/bash
# Daily PostgreSQL backup — add to crontab:
# 0 2 * * * /home/morningbell/morningbell/scripts/db-backup.sh >> /home/morningbell/logs/backup.log 2>&1

BACKUP_DIR="/home/morningbell/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="morningbell_db"
DB_USER="morningbell"
KEEP_DAYS=7

mkdir -p "$BACKUP_DIR"

echo "[$DATE] Starting backup..."
sudo -u postgres pg_dump "$DB_NAME" | gzip > "$BACKUP_DIR/${DB_NAME}_${DATE}.sql.gz"

echo "[$DATE] Backup saved: ${DB_NAME}_${DATE}.sql.gz"

# Remove backups older than KEEP_DAYS
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +$KEEP_DAYS -delete
echo "[$DATE] Old backups cleaned up (kept last $KEEP_DAYS days)"
