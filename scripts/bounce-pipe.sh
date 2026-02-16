#!/bin/bash
# ============================================================
# PowerMTA Bounce Pipe — forwards bounces to Email Engine API
# Called by PowerMTA via accounting pipe:
#   <acct-file |/opt/email-engine/scripts/bounce-pipe.sh>
#       records b
#       map-header-to-column bounce *
#   </acct-file>
#
# Reads CSV bounce records from stdin, classifies them using
# the same category codes as bounce-classifications, and POSTs
# each to the Email Engine API for forwarding to scraper-pro.
#
# Category codes from bounce-classifications:
#   10 = bad-mailbox          -> hard
#   20 = rate-limit           -> soft
#   21 = DNS/sender issues    -> hard
#   22 = quota-issues         -> soft
#   23 = message-size         -> soft
#   24 = timeout              -> soft
#   25 = internal-suppression -> hard
#   26 = smart-send           -> hard
#   30 = protocol             -> soft
#   40 = other                -> soft
#   50 = policy/blocked       -> complaint
#   51 = spam/blacklist       -> complaint
#   52 = content/spam-filter  -> complaint
#   53 = attachment           -> complaint
#   54 = relay                -> soft
#   60 = auto-reply           -> soft (ignore)
#   70 = temporary/greylist   -> soft
#  100 = challenge-response   -> soft
# ============================================================

ENV_FILE="/opt/email-engine/.env"

# Load config
if [ -f "$ENV_FILE" ]; then
    # shellcheck disable=SC1090
    source "$ENV_FILE"
fi

API_URL="http://127.0.0.1:${PORT:-8000}/api/v1/webhooks/pmta-bounce"
API_KEY="${API_KEY:-}"
LOG_FILE="/var/log/email-engine/bounce-pipe.log"

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_FILE")"

# Classify bounce type from PowerMTA bounce category name
# Maps PowerMTA's bounce-category-patterns names to our 3 types
classify_bounce() {
    local category="$1"
    case "$category" in
        # HARD bounces — permanent, remove from list
        bad-mailbox|bad-domain|inactive-mailbox|invalid-mailbox|invalid-sender)
            echo "hard"
            ;;
        routing-errors|no-answer-from-host|bad-connection)
            echo "hard"
            ;;
        # COMPLAINT — spam/policy, remove and flag
        spam-related|policy-related|content-related|virus-related)
            echo "complaint"
            ;;
        relaying-issues)
            echo "complaint"
            ;;
        # SOFT bounces — temporary, retry later
        quota-issues|message-expired|protocol-errors)
            echo "soft"
            ;;
        bad-configuration|other|success)
            echo "soft"
            ;;
        *)
            # Default: treat unknown categories as soft
            echo "soft"
            ;;
    esac
}

# Read bounce records from stdin (CSV from PowerMTA pipe)
# PowerMTA delivers: type,bounceCat,vmta,orig,rcpt,srcMta,dlvSourceIp,jobId,dsnStatus,dsnMta,dsnDiag
while IFS=',' read -r type bounce_cat vmta orig rcpt src_mta dlv_source_ip job_id dsn_status dsn_mta dsn_diag _rest; do
    # Skip empty lines and headers
    [ -z "$rcpt" ] && continue
    [ "$type" = "type" ] && continue

    # Only process bounce records (type=b)
    [ "$type" != "b" ] && continue

    bounce_type=$(classify_bounce "$bounce_cat")

    # Build JSON payload safely using jq (no string interpolation)
    reason_raw="${bounce_cat}: ${dsn_status} ${dsn_diag}"
    if command -v jq >/dev/null 2>&1; then
        payload=$(jq -nc \
            --arg email "$rcpt" \
            --arg bounce_type "$bounce_type" \
            --arg reason "${reason_raw:0:500}" \
            --arg source_ip "$dlv_source_ip" \
            --arg vmta "$vmta" \
            '{email: $email, bounce_type: $bounce_type, reason: $reason, source_ip: $source_ip, vmta: $vmta}')
    else
        # Fallback: sanitize aggressively (strip everything except alphanum, @, ., -, _)
        rcpt_clean=$(printf '%s' "$rcpt" | tr -cd 'a-zA-Z0-9@._-')
        reason_clean=$(printf '%s' "$reason_raw" | tr -cd 'a-zA-Z0-9 ._-:' | cut -c1-500)
        ip_clean=$(printf '%s' "$dlv_source_ip" | tr -cd '0-9.:')
        vmta_clean=$(printf '%s' "$vmta" | tr -cd 'a-zA-Z0-9._-')
        payload="{\"email\":\"${rcpt_clean}\",\"bounce_type\":\"${bounce_type}\",\"reason\":\"${reason_clean}\",\"source_ip\":\"${ip_clean}\",\"vmta\":\"${vmta_clean}\"}"
    fi

    # POST to Email Engine API
    response=$(curl -s -w "%{http_code}" -o /dev/null \
        -X POST "$API_URL" \
        -H "X-API-Key: ${API_KEY}" \
        -H "Content-Type: application/json" \
        -d "$payload" \
        --max-time 5 2>/dev/null)

    if [ "$response" != "200" ] && [ "$response" != "201" ]; then
        echo "$(date -Iseconds) FAIL status=$response email=$rcpt_clean type=$bounce_type cat=$bounce_cat" >> "$LOG_FILE"
    fi
done

exit 0
