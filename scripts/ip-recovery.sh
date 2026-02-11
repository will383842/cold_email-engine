#!/bin/bash
# ============================================================
# Auto-recovery when an IP is blacklisted
# Called by check-blacklists.sh automatically
# ============================================================

set -e

BLACKLISTED_IP="$1"
BLACKLIST_NAME="$2"
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

echo "=== IP Recovery: $BLACKLISTED_IP (blacklisted on $BLACKLIST_NAME) ==="

# 1. PAUSE blacklisted IP (set weight to 0)
cp "$PMTA_CONFIG" "/root/backups/pmta-$(date +%Y%m%d-%H%M).bak"
sed -i "s/${BLACKLISTED_IP} weight 100/${BLACKLISTED_IP} weight 0/" "$PMTA_CONFIG"
sed -i "s/${BLACKLISTED_IP} weight 10/${BLACKLISTED_IP} weight 0/" "$PMTA_CONFIG"
sed -i "s/${BLACKLISTED_IP} weight 20/${BLACKLISTED_IP} weight 0/" "$PMTA_CONFIG"
pmta reload
echo "1. IP paused"

# 2. ACTIVATE next standby
# Find first IP with weight 0 or 10 that is NOT the blacklisted one
STANDBY_ACTIVATED=""
for pattern in "weight 0" "weight 10"; do
    standby_line=$(grep "$pattern" "$PMTA_CONFIG" | grep -v "$BLACKLISTED_IP" | head -1)
    if [ -n "$standby_line" ]; then
        # Extract the IP pattern and set to weight 100
        standby_ip=$(echo "$standby_line" | grep -oP '\d+\.\d+\.\d+\.\d+')
        if [ -n "$standby_ip" ]; then
            sed -i "s/${standby_ip} weight [0-9]*/${standby_ip} weight 100/" "$PMTA_CONFIG"
            pmta reload
            STANDBY_ACTIVATED="$standby_ip"
            echo "2. Standby activated: $standby_ip"
            break
        fi
    fi
done

# 3. Analyze cause
BOUNCE_RATE="unknown"
if [ -f /var/log/pmta/acct.csv ]; then
    TOTAL=$(grep "$BLACKLISTED_IP" /var/log/pmta/acct.csv | tail -1000 | wc -l)
    BOUNCES=$(grep "$BLACKLISTED_IP" /var/log/pmta/acct.csv | tail -1000 | grep -c "bounce" || true)
    if [ "$TOTAL" -gt 0 ]; then
        BOUNCE_RATE=$(echo "scale=2; ($BOUNCES/$TOTAL)*100" | bc)
    fi
fi
echo "3. Bounce rate: ${BOUNCE_RATE}%"

# 4. Quarantine for 30 days
echo "${BLACKLISTED_IP}:$(date +%s):${BLACKLIST_NAME}:quarantine_30d" >> /var/lib/ip-quarantine.txt
echo "4. IP quarantined for 30 days"

# 5. Notify
alert_telegram "✅ <b>IP Recovery Complete</b>
Blacklisted IP: <code>$BLACKLISTED_IP</code>
Blacklist: <code>$BLACKLIST_NAME</code>
Standby activated: <code>${STANDBY_ACTIVATED:-none}</code>
Bounce rate: ${BOUNCE_RATE}%
Quarantine: 30 days"

echo "=== Recovery complete ==="
