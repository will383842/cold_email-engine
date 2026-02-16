#!/bin/bash
# ============================================================
# PowerMTA Delivery Pipe — reports delivery stats to Email Engine
# Called by PowerMTA via accounting pipe:
#   <acct-file |/opt/email-engine/scripts/delivery-pipe.sh>
#       records d
#       map-header-to-column delivery *
#   </acct-file>
#
# Reads CSV delivery records from stdin, aggregates by domain,
# and POSTs batch delivery counts to Email Engine API.
# Email Engine forwards to scraper-pro for bounce rate calculation.
# ============================================================

ENV_FILE="/opt/email-engine/.env"

# Load config
if [ -f "$ENV_FILE" ]; then
    # shellcheck disable=SC1090
    source "$ENV_FILE"
fi

API_URL="http://127.0.0.1:${PORT:-8000}/api/v1/webhooks/pmta-delivery"
API_KEY="${API_KEY:-}"
LOG_FILE="/var/log/email-engine/delivery-pipe.log"

mkdir -p "$(dirname "$LOG_FILE")"

# Associative array to aggregate deliveries by domain
declare -A domain_counts

# Read delivery records from stdin (CSV from PowerMTA pipe)
# PowerMTA delivers: type,vmta,orig,rcpt,sourceMta,dlvSourceIp,jobId,dsnStatus,dsnMta,dsnDiag
while IFS=',' read -r type vmta orig rcpt src_mta dlv_source_ip job_id dsn_status dsn_mta dsn_diag _rest; do
    # Skip empty lines and headers
    [ -z "$rcpt" ] && continue
    [ "$type" = "type" ] && continue

    # Only process delivery records (type=d)
    [ "$type" != "d" ] && continue

    # Extract domain from recipient
    domain="${rcpt##*@}"
    domain=$(echo "$domain" | tr -d '"\\' | tr '[:upper:]' '[:lower:]')

    [ -z "$domain" ] && continue

    # Increment domain count
    domain_counts["$domain"]=$(( ${domain_counts["$domain"]:-0} + 1 ))
done

# POST aggregated delivery counts per domain
for domain in "${!domain_counts[@]}"; do
    count="${domain_counts[$domain]}"

    payload="{\"domain\":\"${domain}\",\"count\":${count}}"

    response=$(curl -s -w "%{http_code}" -o /dev/null \
        -X POST "$API_URL" \
        -H "X-API-Key: ${API_KEY}" \
        -H "Content-Type: application/json" \
        -d "$payload" \
        --max-time 5 2>/dev/null)

    if [ "$response" != "200" ] && [ "$response" != "201" ]; then
        echo "$(date -Iseconds) FAIL status=$response domain=$domain count=$count" >> "$LOG_FILE"
    fi
done

exit 0
