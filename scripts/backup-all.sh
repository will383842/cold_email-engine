#!/bin/bash
# ============================================================
# Daily backup of all email engine data
# Cron: 0 2 * * * (2am daily)
# ============================================================

set -e

source /root/.email-engine.env 2>/dev/null || true

BACKUP_DIR="/backups/$(date +%Y-%m-%d)"
mkdir -p "$BACKUP_DIR"

echo "=== Backup $(date) ==="

# Backup MailWizz database
if [ -n "$MAILWIZZ_DB_PASS" ]; then
    mysqldump -u "${MAILWIZZ_DB_USER:-mailwizz}" -p"$MAILWIZZ_DB_PASS" \
        "${MAILWIZZ_DB_NAME:-mailwizz}" | gzip > "$BACKUP_DIR/mailwizz-db.sql.gz"
    echo "OK: MailWizz DB"
fi

# Backup MailWizz files
if [ -d /var/www/html/mailwizz ]; then
    tar -czf "$BACKUP_DIR/mailwizz-files.tar.gz" /var/www/html/mailwizz 2>/dev/null
    echo "OK: MailWizz files"
fi

# Backup PowerMTA config
if [ -f /etc/pmta/config ]; then
    cp /etc/pmta/config "$BACKUP_DIR/pmta-config"
    echo "OK: PowerMTA config"
fi

# Backup DKIM keys
if [ -d /etc/pmta/dkim ]; then
    cp -r /etc/pmta/dkim "$BACKUP_DIR/pmta-dkim"
    echo "OK: DKIM keys"
fi

# Backup IP quarantine
if [ -f /var/lib/ip-quarantine.txt ]; then
    cp /var/lib/ip-quarantine.txt "$BACKUP_DIR/"
    echo "OK: IP quarantine"
fi

# Cleanup old backups (>30 days)
find /backups -type d -mtime +30 -exec rm -rf {} \; 2>/dev/null || true

echo "=== Backup complete: $BACKUP_DIR ==="
