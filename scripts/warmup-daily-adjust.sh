#!/bin/bash
# ============================================================
# Daily warm-up quota adjustment
# Cron: 0 0 * * * (midnight daily)
# Adjusts MailWizz delivery server quotas during warm-up period
# ============================================================

set -e

source /root/.email-engine.env 2>/dev/null || true

MAILWIZZ_DB_USER="${MAILWIZZ_DB_USER:-mailwizz}"
MAILWIZZ_DB_PASS="${MAILWIZZ_DB_PASS}"
MAILWIZZ_DB_NAME="${MAILWIZZ_DB_NAME:-mailwizz}"

TELEGRAM_TOKEN="${TELEGRAM_BOT_TOKEN}"
TELEGRAM_CHAT="${TELEGRAM_CHAT_ID}"

alert_telegram() {
    local message="$1"
    if [ -n "$TELEGRAM_TOKEN" ] && [ -n "$TELEGRAM_CHAT" ]; then
        curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_TOKEN}/sendMessage" \
             -d chat_id="$TELEGRAM_CHAT" \
             -d text="$message" \
             -d parse_mode="HTML" > /dev/null 2>&1
    fi
}

adjust_quota() {
    local server_id=$1
    local server_name=$2
    local increment_pct=$3

    # Get current quota
    current_quota=$(mysql -u "$MAILWIZZ_DB_USER" -p"$MAILWIZZ_DB_PASS" "$MAILWIZZ_DB_NAME" -N -e \
        "SELECT daily_quota FROM mw_delivery_server WHERE server_id = $server_id;")

    if [ -z "$current_quota" ] || [ "$current_quota" = "0" ]; then
        echo "SKIP: Server $server_name (id=$server_id) - no quota set"
        return
    fi

    # Calculate new quota
    new_quota=$((current_quota + (current_quota * increment_pct / 100)))

    # Update MailWizz
    mysql -u "$MAILWIZZ_DB_USER" -p"$MAILWIZZ_DB_PASS" "$MAILWIZZ_DB_NAME" -e \
        "UPDATE mw_delivery_server
         SET daily_quota = $new_quota,
             hourly_quota = CEIL($new_quota / 24)
         WHERE server_id = $server_id;"

    echo "OK: $server_name: $current_quota -> $new_quota/day (+${increment_pct}%)"
}

echo "=== Daily Warm-Up Adjustment - $(date) ==="

# Adjust servers in warm-up phase
# Server IDs must match your MailWizz delivery server configuration
# Uncomment and configure when MailWizz is installed:

# adjust_quota 1 "Trans (IP1)" 50
# adjust_quota 2 "Marketing (IP2)" 50
# adjust_quota 3 "Cold (IP3)" 100

echo "=== Warm-up adjustment complete ==="

# alert_telegram "📈 <b>Warm-Up Adjustment</b>
# Date: $(date +%Y-%m-%d)
# Quotas updated for warm-up servers"
