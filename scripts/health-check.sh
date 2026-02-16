#!/bin/bash
# ============================================================
# System health check (standalone fallback)
# NOTE: APScheduler runs health checks every 5 min automatically.
#       This script is a FALLBACK only — do NOT add to cron
#       unless APScheduler is disabled.
# ============================================================

set -e

ENV_FILE="/opt/email-engine/.env"
if [ -f "$ENV_FILE" ]; then
    # shellcheck disable=SC1090
    source "$ENV_FILE"
fi

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

ISSUES=""

# Check PowerMTA
if pgrep -x "pmta" > /dev/null 2>&1; then
    # Check queue size
    queue_size=$(pmta show queue 2>/dev/null | grep -oP '\d+(?= messages)' || echo "0")
    if [ "${queue_size:-0}" -gt 10000 ]; then
        ISSUES="${ISSUES}\n- PowerMTA queue: ${queue_size} messages"
    fi
else
    ISSUES="${ISSUES}\n- PowerMTA DOWN"
    systemctl restart powermta 2>/dev/null || true
fi

# Check disk space
disk_usage=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "${disk_usage:-0}" -gt 85 ]; then
    ISSUES="${ISSUES}\n- Disk usage: ${disk_usage}%"
fi

# Check RAM
ram_usage=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
if [ "${ram_usage:-0}" -gt 90 ]; then
    ISSUES="${ISSUES}\n- RAM usage: ${ram_usage}%"
fi

# Report if issues found
if [ -n "$ISSUES" ]; then
    alert_telegram "⚠️ <b>Health Check Alert</b>
Server: VDS PowerMTA
Time: $(date +%H:%M)
Issues:${ISSUES}"
fi
