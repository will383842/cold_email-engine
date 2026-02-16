#!/bin/bash
# ============================================================
# Monthly IP rotation for cold email pool
# NOTE: APScheduler runs monthly rotation automatically.
#       This script is a FALLBACK only — do NOT add to cron
#       unless APScheduler is disabled.
#
# Rotation cycle:
#   Active  (weight 100) -> Retiring (weight 10)
#   Warming (weight  20) -> Active   (weight 100)
#   Retiring(weight  10) -> Resting  (weight 0)
#   Resting (weight   0) -> Warming  (weight 20)
# ============================================================

set -e

PMTA_CONFIG="/etc/pmta/config"

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

# Escape dots in IP for safe sed usage
escape_ip() {
    echo "$1" | sed 's/\./\\./g'
}

echo "=== Monthly IP Rotation - $(date) ==="

# Backup config
mkdir -p /root/backups
cp "$PMTA_CONFIG" "/root/backups/pmta-rotation-$(date +%Y%m%d).bak"

echo "Current pool-cold weights:"
grep -A 10 "pool-cold" "$PMTA_CONFIG" | grep "weight" || echo "(no pool-cold found)"

# Parse current weights from pool-cold section
# Format: virtual-mta mta-xxx weight NNN
CHANGES=""

# Step 1: Active (100) -> Retiring (10)
while IFS= read -r line; do
    ip=$(echo "$line" | grep -oP '\d+\.\d+\.\d+\.\d+' || true)
    mta=$(echo "$line" | grep -oP 'virtual-mta \S+' | awk '{print $2}' || true)
    if [ -n "$mta" ]; then
        escaped=$(escape_ip "$ip")
        sed -i "s/\(${mta:-$escaped}\) weight 100/\1 weight 10/" "$PMTA_CONFIG"
        CHANGES="${CHANGES}\n  ${mta}: 100 -> 10 (retiring)"
    fi
done < <(grep -A 10 "pool-cold" "$PMTA_CONFIG" | grep "weight 100" || true)

# Step 2: Warming (20) -> Active (100)
while IFS= read -r line; do
    mta=$(echo "$line" | grep -oP 'virtual-mta \S+' | awk '{print $2}' || true)
    if [ -n "$mta" ]; then
        sed -i "s/\(${mta}\) weight 20/\1 weight 100/" "$PMTA_CONFIG"
        CHANGES="${CHANGES}\n  ${mta}: 20 -> 100 (active)"
    fi
done < <(grep -A 10 "pool-cold" "$PMTA_CONFIG" | grep "weight 20" || true)

# Step 3: Retiring (10) -> Resting (0)
while IFS= read -r line; do
    mta=$(echo "$line" | grep -oP 'virtual-mta \S+' | awk '{print $2}' || true)
    if [ -n "$mta" ]; then
        sed -i "s/\(${mta}\) weight 10/\1 weight 0/" "$PMTA_CONFIG"
        CHANGES="${CHANGES}\n  ${mta}: 10 -> 0 (resting)"
    fi
done < <(grep -A 10 "pool-cold" "$PMTA_CONFIG" | grep "weight 10" || true)

# Step 4: Resting (0) -> Warming (20)
while IFS= read -r line; do
    mta=$(echo "$line" | grep -oP 'virtual-mta \S+' | awk '{print $2}' || true)
    if [ -n "$mta" ]; then
        sed -i "s/\(${mta}\) weight 0/\1 weight 20/" "$PMTA_CONFIG"
        CHANGES="${CHANGES}\n  ${mta}: 0 -> 20 (warming)"
    fi
done < <(grep -A 10 "pool-cold" "$PMTA_CONFIG" | grep "weight 0" || true)

# Reload PowerMTA
pmta reload

echo ""
echo "New pool-cold weights:"
grep -A 10 "pool-cold" "$PMTA_CONFIG" | grep "weight" || echo "(no pool-cold found)"

if [ -n "$CHANGES" ]; then
    alert_telegram "🔄 <b>Monthly IP Rotation</b>
Date: $(date +%Y-%m-%d)
Changes:${CHANGES}"
else
    alert_telegram "🔄 <b>Monthly IP Rotation</b>
Date: $(date +%Y-%m-%d)
Status: No changes needed"
fi

echo "=== Rotation complete ==="
