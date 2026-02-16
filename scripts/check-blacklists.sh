#!/bin/bash
# ============================================================
# Check all IPs against major blacklists (standalone fallback)
# NOTE: APScheduler runs blacklist checks every 4h automatically.
#       This script is a FALLBACK only — do NOT add to cron
#       unless APScheduler is disabled.
# ============================================================

set -e

ENV_FILE="/opt/email-engine/.env"
if [ -f "$ENV_FILE" ]; then
    # shellcheck disable=SC1090
    source "$ENV_FILE"
fi

# IPs to check — loaded from Email Engine API if available, else from config
API_URL="http://127.0.0.1:${PORT:-8000}/api/v1/ips"
IPS=()

if [ -n "$API_KEY" ]; then
    # Fetch active/warming IPs from the API
    api_ips=$(curl -s -H "X-API-Key: ${API_KEY}" "$API_URL" 2>/dev/null \
        | grep -oP '"address"\s*:\s*"\K[^"]+' || true)
    if [ -n "$api_ips" ]; then
        while IFS= read -r ip; do
            IPS+=("$ip")
        done <<< "$api_ips"
    fi
fi

if [ ${#IPS[@]} -eq 0 ]; then
    echo "ERROR: No IPs found. Check API or add IPs manually."
    exit 1
fi

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
    # Validate IP format
    if ! echo "$ip" | grep -qP '^\d+\.\d+\.\d+\.\d+$'; then
        echo "SKIP: Invalid IP format: $ip"
        continue
    fi

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
            SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
            "$SCRIPT_DIR/ip-recovery.sh" "$ip" "$bl" 2>/dev/null || true
        fi
    done
done

if [ $FOUND_BLACKLISTED -eq 0 ]; then
    echo "$(date): All ${#IPS[@]} IPs clean"
fi
