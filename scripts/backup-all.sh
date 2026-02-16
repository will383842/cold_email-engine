#!/bin/bash
# ============================================================
# Daily backup of all email engine data
# Cron: 0 2 * * * (2am daily)
# ============================================================

set -e

ENV_FILE="/opt/email-engine/.env"
if [ -f "$ENV_FILE" ]; then
    # shellcheck disable=SC1090
    source "$ENV_FILE"
fi

BACKUP_DIR="/backups/$(date +%Y-%m-%d)"
mkdir -p "$BACKUP_DIR"

echo "=== Backup $(date) ==="

ERRORS=0

# Backup MailWizz database (use MYSQL_PWD env var to avoid password in ps output)
if [ -n "$MAILWIZZ_DB_PASSWORD" ]; then
    MYSQL_PWD="$MAILWIZZ_DB_PASSWORD" mysqldump -u "${MAILWIZZ_DB_USER:-mailwizz}" \
        "${MAILWIZZ_DB_NAME:-mailwizz}" 2>/dev/null | gzip > "$BACKUP_DIR/mailwizz-db.sql.gz"
    if gzip -t "$BACKUP_DIR/mailwizz-db.sql.gz" 2>/dev/null; then
        echo "OK: MailWizz DB"
    else
        echo "FAIL: MailWizz DB backup corrupted"
        ERRORS=$((ERRORS + 1))
    fi
fi

# Backup MailWizz files
if [ -d /var/www/html/mailwizz ]; then
    tar -czf "$BACKUP_DIR/mailwizz-files.tar.gz" /var/www/html/mailwizz 2>/dev/null
    if tar -tzf "$BACKUP_DIR/mailwizz-files.tar.gz" > /dev/null 2>&1; then
        echo "OK: MailWizz files"
    else
        echo "FAIL: MailWizz files backup corrupted"
        ERRORS=$((ERRORS + 1))
    fi
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

# Backup Email Engine database
if [ -f /opt/email-engine/email_engine.db ]; then
    cp /opt/email-engine/email_engine.db "$BACKUP_DIR/email_engine.db"
    echo "OK: Email Engine DB"
fi

# Backup IP quarantine
if [ -f /var/lib/ip-quarantine.txt ]; then
    cp /var/lib/ip-quarantine.txt "$BACKUP_DIR/"
    echo "OK: IP quarantine"
fi

# Create checksum file for verification
cd "$BACKUP_DIR" && sha256sum * > checksums.sha256 2>/dev/null
echo "OK: Checksums generated"

# Cleanup old backups (>90 days)
find /backups -maxdepth 1 -type d -mtime +90 -exec rm -rf {} \; 2>/dev/null || true

# Report status
if [ $ERRORS -gt 0 ]; then
    echo "=== Backup COMPLETED WITH $ERRORS ERRORS ==="
    # Alert via Telegram if available
    if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$TELEGRAM_CHAT_ID" ]; then
        curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
             -d chat_id="$TELEGRAM_CHAT_ID" \
             -d text="⚠️ <b>Backup Warning</b>%0ADate: $(date +%Y-%m-%d)%0AErrors: $ERRORS" \
             -d parse_mode="HTML" > /dev/null 2>&1
    fi
    exit 1
else
    echo "=== Backup complete: $BACKUP_DIR ==="
fi
