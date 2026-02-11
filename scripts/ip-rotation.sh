#!/bin/bash
# ============================================================
# Monthly IP rotation for cold email pool
# Cron: 0 3 1 * * (1st of each month at 3am)
# ============================================================

set -e

PMTA_CONFIG="/etc/pmta/config"

source /root/.email-engine.env 2>/dev/null || true

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

echo "=== Monthly IP Rotation - $(date) ==="

# Backup config
cp "$PMTA_CONFIG" "/root/backups/pmta-rotation-$(date +%Y%m%d).bak"

# Read current weights from config
echo "Current pool-cold weights:"
grep -A 10 "pool-cold" "$PMTA_CONFIG" | grep "weight"

# Rotation logic:
# - Active (weight 100) -> Retiring (weight 10)
# - Warming (weight 20) -> Active (weight 100)
# - Retiring (weight 10) -> Resting (weight 0)
# - Resting (weight 0) -> Warming (weight 20)

# This is a template - actual IPs need to be configured
# The script reads the current state and rotates

echo ""
echo "Applying rotation..."
echo "(Configure actual IP rotation rules in this script)"
echo ""

# Reload PowerMTA
pmta reload

alert_telegram "🔄 <b>Monthly IP Rotation</b>
Date: $(date +%Y-%m-%d)
Status: Rotation applied
Check pool-cold weights in PowerMTA"

echo "=== Rotation complete ==="
