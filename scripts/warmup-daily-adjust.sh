#!/bin/bash
# ============================================================
# Daily warm-up quota adjustment (standalone fallback)
# NOTE: APScheduler runs warmup daily tick automatically.
#       This script is a FALLBACK only — do NOT add to cron
#       unless APScheduler is disabled.
#
# Adjusts MailWizz delivery server quotas during warm-up period
# ============================================================

set -e

ENV_FILE="/opt/email-engine/.env"
if [ -f "$ENV_FILE" ]; then
    # shellcheck disable=SC1090
    source "$ENV_FILE"
fi

MAILWIZZ_DB_USER="${MAILWIZZ_DB_USER:-mailwizz}"
MAILWIZZ_DB_PASS="${MAILWIZZ_DB_PASSWORD}"
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
    local max_quota=${4:-10000}

    # Get current quota (parameterized query via printf)
    current_quota=$(mysql -u "$MAILWIZZ_DB_USER" -p"$MAILWIZZ_DB_PASS" "$MAILWIZZ_DB_NAME" -N -e \
        "SELECT daily_quota FROM mw_delivery_server WHERE server_id = $(printf '%d' "$server_id");")

    if [ -z "$current_quota" ] || [ "$current_quota" = "0" ]; then
        echo "SKIP: Server $server_name (id=$server_id) - no quota set"
        return
    fi

    # Calculate new quota with cap
    new_quota=$((current_quota + (current_quota * increment_pct / 100)))
    if [ "$new_quota" -gt "$max_quota" ]; then
        new_quota=$max_quota
    fi

    if [ "$new_quota" -eq "$current_quota" ]; then
        echo "SKIP: $server_name already at max ($max_quota/day)"
        return
    fi

    # Update MailWizz
    mysql -u "$MAILWIZZ_DB_USER" -p"$MAILWIZZ_DB_PASS" "$MAILWIZZ_DB_NAME" -e \
        "UPDATE mw_delivery_server
         SET daily_quota = $(printf '%d' "$new_quota"),
             hourly_quota = CEIL($(printf '%d' "$new_quota") / 24)
         WHERE server_id = $(printf '%d' "$server_id");"

    echo "OK: $server_name: $current_quota -> $new_quota/day (+${increment_pct}%, max=$max_quota)"
}

echo "=== Daily Warm-Up Adjustment - $(date) ==="

if [ -z "$MAILWIZZ_DB_PASS" ]; then
    echo "ERROR: MAILWIZZ_DB_PASSWORD not set in .env"
    exit 1
fi

# Dynamically discover delivery servers and adjust
# List all active servers with their current quotas
SERVERS=$(mysql -u "$MAILWIZZ_DB_USER" -p"$MAILWIZZ_DB_PASS" "$MAILWIZZ_DB_NAME" -N -e \
    "SELECT server_id, name, daily_quota FROM mw_delivery_server WHERE status = 'active';" 2>/dev/null || true)

if [ -z "$SERVERS" ]; then
    echo "No active delivery servers found (MailWizz may not be installed yet)"
    echo "To configure manually, edit this script and uncomment the lines below:"
    echo "# adjust_quota 1 \"Trans (IP1)\" 50 200"
    echo "# adjust_quota 2 \"Marketing (IP2)\" 50 500"
    echo "# adjust_quota 3 \"Cold (IP3)\" 100 1000"
else
    CHANGES=""
    while IFS=$'\t' read -r sid sname squota; do
        # Default: 50% increment, 10000 max
        before=$squota
        adjust_quota "$sid" "$sname" 50 10000
        CHANGES="${CHANGES}\n  $sname: $before -> adjusted"
    done <<< "$SERVERS"

    if [ -n "$CHANGES" ]; then
        alert_telegram "📈 <b>Warm-Up Adjustment</b>
Date: $(date +%Y-%m-%d)
Servers adjusted:${CHANGES}"
    fi
fi

echo "=== Warm-up adjustment complete ==="
