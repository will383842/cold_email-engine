#!/bin/bash
# ============================================================
# Check all IPs against major blacklists
# Cron: 0 */4 * * * (every 4 hours)
# ============================================================

set -e

# Load config
source /root/.email-engine.env 2>/dev/null || true

# IPs to check (replace with real IPs)
IPS=(
    "IP1_ADDRESS"
    "IP2_ADDRESS"
    "IP3_ADDRESS"
    "IP4_ADDRESS"
    "IP5_ADDRESS"
)

BLACKLISTS=(
    "zen.spamhaus.org"
    "bl.spamcop.net"
    "b.barracudacentral.org"
    "dnsbl.sorbs.net"
    "cbl.abuseat.org"
    "dnsbl-1.uceprotect.net"
    "psbl.surriel.com"
    "dyna.spamrats.com"
    "bl.mailspike.net"
)

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

FOUND_BLACKLISTED=0

for ip in "${IPS[@]}"; do
    # Reverse IP for DNS lookup
    reversed_ip=$(echo "$ip" | awk -F. '{print $4"."$3"."$2"."$1}')

    for bl in "${BLACKLISTS[@]}"; do
        if host "${reversed_ip}.${bl}" > /dev/null 2>&1; then
            FOUND_BLACKLISTED=1
            echo "BLACKLISTED: $ip on $bl"

            alert_telegram "🚨 <b>IP BLACKLISTED</b>
IP: <code>$ip</code>
Blacklist: <code>$bl</code>
Action: Running auto-recovery..."

            # Trigger auto-recovery
            /root/scripts/ip-recovery.sh "$ip" "$bl" 2>/dev/null || true
        fi
    done
done

if [ $FOUND_BLACKLISTED -eq 0 ]; then
    echo "$(date): All IPs clean"
fi
