#!/bin/bash
# ============================================================
# Auto-recovery when an IP is blacklisted
# Called by check-blacklists.sh or manually
# Usage: ip-recovery.sh <IP_ADDRESS> <BLACKLIST_NAME>
# ============================================================

set -e

BLACKLISTED_IP="$1"
BLACKLIST_NAME="$2"
PMTA_CONFIG="/etc/pmta/config"

if [ -z "$BLACKLISTED_IP" ] || [ -z "$BLACKLIST_NAME" ]; then
    echo "Usage: $0 <IP_ADDRESS> <BLACKLIST_NAME>"
    exit 1
fi

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

# Escape dots in IP for safe use in sed regex
escape_ip() {
    echo "$1" | sed 's/\./\\./g'
}

echo "=== IP Recovery: $BLACKLISTED_IP (blacklisted on $BLACKLIST_NAME) ==="

# 1. PAUSE blacklisted IP (set weight to 0)
mkdir -p /root/backups
cp "$PMTA_CONFIG" "/root/backups/pmta-$(date +%Y%m%d-%H%M).bak"

ESCAPED_IP=$(escape_ip "$BLACKLISTED_IP")
sed -i "s/${ESCAPED_IP} weight [0-9]*/${BLACKLISTED_IP} weight 0/g" "$PMTA_CONFIG"
pmta reload
echo "1. IP paused (weight 0)"

# 2. ACTIVATE next standby
# Find first IP with weight 0 that is NOT the blacklisted one
STANDBY_ACTIVATED=""
while IFS= read -r standby_line; do
    [ -z "$standby_line" ] && continue
    standby_ip=$(echo "$standby_line" | grep -oP '\d+\.\d+\.\d+\.\d+' || true)
    if [ -n "$standby_ip" ] && [ "$standby_ip" != "$BLACKLISTED_IP" ]; then
        ESCAPED_STANDBY=$(escape_ip "$standby_ip")
        sed -i "s/${ESCAPED_STANDBY} weight 0/${standby_ip} weight 100/" "$PMTA_CONFIG"
        pmta reload
        STANDBY_ACTIVATED="$standby_ip"
        echo "2. Standby activated: $standby_ip"
        break
    fi
done < <(grep "weight 0" "$PMTA_CONFIG" | grep -v "$BLACKLISTED_IP" 2>/dev/null || true)

if [ -z "$STANDBY_ACTIVATED" ]; then
    echo "2. WARNING: No standby IP available to activate"
fi

# 3. Analyze bounce rate from recent logs
BOUNCE_RATE="unknown"
if [ -f /var/log/pmta/acct.csv ]; then
    # Use time-based window: last 7 days of data
    WEEK_AGO=$(date -d '7 days ago' +%Y-%m-%d 2>/dev/null || date -v-7d +%Y-%m-%d 2>/dev/null || echo "")
    if [ -n "$WEEK_AGO" ]; then
        TOTAL=$(grep "$BLACKLISTED_IP" /var/log/pmta/acct.csv | awk -F',' -v d="$WEEK_AGO" '$1 >= d' | wc -l)
        BOUNCES=$(grep "$BLACKLISTED_IP" /var/log/pmta/acct.csv | awk -F',' -v d="$WEEK_AGO" '$1 >= d' | grep -c "bounce" || true)
    else
        TOTAL=$(grep -c "$BLACKLISTED_IP" /var/log/pmta/acct.csv || echo "0")
        BOUNCES=$(grep "$BLACKLISTED_IP" /var/log/pmta/acct.csv | grep -c "bounce" || true)
    fi
    if [ "${TOTAL:-0}" -gt 0 ]; then
        BOUNCE_RATE=$(echo "scale=2; (${BOUNCES:-0}/${TOTAL})*100" | bc 2>/dev/null || echo "unknown")
    fi
fi
echo "3. Bounce rate: ${BOUNCE_RATE}%"

# 4. Quarantine for 30 days
mkdir -p /var/lib
touch /var/lib/ip-quarantine.txt
# Use flock to prevent concurrent write corruption
(
    flock -w 5 200
    echo "${BLACKLISTED_IP}:$(date +%s):${BLACKLIST_NAME}:quarantine_30d" >> /var/lib/ip-quarantine.txt
) 200>/var/lib/ip-quarantine.lock
echo "4. IP quarantined for 30 days"

# 5. Notify via Email Engine API
if [ -n "$API_KEY" ]; then
    curl -s -X PATCH "http://127.0.0.1:${PORT:-8000}/api/v1/ips" \
        -H "X-API-Key: ${API_KEY}" \
        -H "Content-Type: application/json" \
        -d "{\"status\": \"blacklisted\"}" > /dev/null 2>&1 || true
fi

# 6. Telegram alert
alert_telegram "✅ <b>IP Recovery Complete</b>
Blacklisted IP: <code>$BLACKLISTED_IP</code>
Blacklist: <code>$BLACKLIST_NAME</code>
Standby activated: <code>${STANDBY_ACTIVATED:-none}</code>
Bounce rate: ${BOUNCE_RATE}%
Quarantine: 30 days"

echo "=== Recovery complete ==="
