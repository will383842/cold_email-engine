#!/bin/bash
################################################################################
# PROTECTION BLACKLIST - Monitoring & Auto-Healing
# Check RBL, IP rotation, alertes
################################################################################

set -e

# Configuration
API_URL="${API_URL:-http://localhost:8000}"
API_KEY="${API_KEY}"
SLACK_WEBHOOK="${SLACK_WEBHOOK}"
EMAIL_ALERT="${EMAIL_ALERT:-admin@sos-holidays.com}"

# RBL Lists à checker
RBL_LISTS=(
    "zen.spamhaus.org"
    "b.barracudacentral.org"
    "bl.spamcop.net"
    "dnsbl.sorbs.net"
    "spam.dnsbl.sorbs.net"
    "ips.backscatterer.org"
    "ix.dnsbl.manitu.net"
    "psbl.surriel.com"
    "ubl.unsubscore.com"
    "dnsbl-1.uceprotect.net"
)

echo "═══════════════════════════════════════════════════════════"
echo "  PROTECTION BLACKLIST - Monitoring"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "═══════════════════════════════════════════════════════════"
echo ""

# ═══════════════════════════════════════════════════════════
# FONCTION : Check si IP blacklistée sur RBL
# ═══════════════════════════════════════════════════════════
check_rbl() {
    local ip=$1
    local blacklisted=0
    local rbl_found=""

    # Inverser IP pour lookup DNS
    local reversed_ip=$(echo $ip | awk -F. '{print $4"."$3"."$2"."$1}')

    for rbl in "${RBL_LISTS[@]}"; do
        if host ${reversed_ip}.${rbl} >/dev/null 2>&1; then
            blacklisted=1
            rbl_found="${rbl_found}${rbl}, "
        fi
    done

    if [ $blacklisted -eq 1 ]; then
        echo "❌ $ip : BLACKLISTÉE sur ${rbl_found%%, }"
        send_alert "⚠️ IP $ip blacklistée" "RBL: ${rbl_found%%, }"
        pause_ip "$ip"
    else
        echo "✅ $ip : Clean (aucune RBL)"
    fi

    return $blacklisted
}

# ═══════════════════════════════════════════════════════════
# FONCTION : Pause IP
# ═══════════════════════════════════════════════════════════
pause_ip() {
    local ip=$1

    echo "  → Pause IP $ip via API..."
    curl -s -X PATCH "${API_URL}/api/v1/ips/${ip}" \
        -H "X-API-KEY: ${API_KEY}" \
        -H "Content-Type: application/json" \
        -d "{\"status\": \"paused\", \"reason\": \"Blacklisted on RBL\"}"

    echo "  → IP $ip mise en pause"
}

# ═══════════════════════════════════════════════════════════
# FONCTION : Envoyer alerte
# ═══════════════════════════════════════════════════════════
send_alert() {
    local title=$1
    local message=$2

    # Slack
    if [ ! -z "$SLACK_WEBHOOK" ]; then
        curl -s -X POST "$SLACK_WEBHOOK" \
            -H "Content-Type: application/json" \
            -d "{
                \"text\": \"$title\",
                \"blocks\": [{
                    \"type\": \"section\",
                    \"text\": {
                        \"type\": \"mrkdwn\",
                        \"text\": \"*$title*\\n$message\"
                    }
                }]
            }"
    fi

    # Email (via sendmail)
    if [ ! -z "$EMAIL_ALERT" ]; then
        echo -e "Subject: [EMAIL-ENGINE] $title\n\n$message" | \
            sendmail "$EMAIL_ALERT"
    fi
}

# ═══════════════════════════════════════════════════════════
# FONCTION : Check reputation score
# ═══════════════════════════════════════════════════════════
check_reputation() {
    local ip=$1

    # Récupérer stats via API
    local stats=$(curl -s "${API_URL}/api/v1/ips/${ip}/stats" \
        -H "X-API-KEY: ${API_KEY}")

    local bounce_rate=$(echo $stats | jq -r '.bounce_rate // 0')
    local complaint_rate=$(echo $stats | jq -r '.complaint_rate // 0')
    local open_rate=$(echo $stats | jq -r '.open_rate // 0')

    # Calcul score (0-100)
    local score=100

    # Pénalités
    if (( $(echo "$bounce_rate > 0.05" | bc -l) )); then
        score=$((score - 30))  # Bounce > 5% = -30 pts
    fi

    if (( $(echo "$complaint_rate > 0.001" | bc -l) )); then
        score=$((score - 40))  # Complaint > 0.1% = -40 pts
    fi

    if (( $(echo "$open_rate < 0.10" | bc -l) )); then
        score=$((score - 20))  # Open < 10% = -20 pts
    fi

    echo "  Score : $score/100 (bounce: ${bounce_rate}, complaint: ${complaint_rate}, open: ${open_rate})"

    # Actions selon score
    if [ $score -lt 50 ]; then
        echo "  ⚠️  Score critique ($score) → Pause IP"
        pause_ip "$ip"
        send_alert "IP $ip score critique" "Score: $score/100\nBounce: ${bounce_rate}\nComplaint: ${complaint_rate}"
    elif [ $score -lt 70 ]; then
        echo "  ⚠️  Score faible ($score) → Ralentissement"
        curl -s -X PATCH "${API_URL}/api/v1/ips/${ip}" \
            -H "X-API-KEY: ${API_KEY}" \
            -H "Content-Type: application/json" \
            -d "{\"throttle\": 0.5}"
    fi
}

# ═══════════════════════════════════════════════════════════
# FONCTION : List hygiene (supprimer bounces)
# ═══════════════════════════════════════════════════════════
clean_bounces() {
    echo ""
    echo "═══════════════════════════════════════════════════════════"
    echo "  LIST HYGIENE - Nettoyage bounces"
    echo "═══════════════════════════════════════════════════════════"

    # Récupérer hard bounces via API
    local bounces=$(curl -s "${API_URL}/api/v1/bounces?type=hard" \
        -H "X-API-KEY: ${API_KEY}")

    local count=$(echo $bounces | jq -r '. | length')
    echo "  Hard bounces trouvés : $count"

    if [ $count -gt 0 ]; then
        echo "  → Suppression automatique..."
        curl -s -X DELETE "${API_URL}/api/v1/contacts/bounced" \
            -H "X-API-KEY: ${API_KEY}"
        echo "  ✓ $count contacts supprimés"
    fi
}

# ═══════════════════════════════════════════════════════════
# FONCTION : Engagement tracking
# ═══════════════════════════════════════════════════════════
clean_inactive() {
    echo ""
    echo "═══════════════════════════════════════════════════════════"
    echo "  ENGAGEMENT - Nettoyage contacts inactifs"
    echo "═══════════════════════════════════════════════════════════"

    # Contacts jamais ouvert depuis 180 jours
    local inactive=$(curl -s "${API_URL}/api/v1/contacts/inactive?days=180" \
        -H "X-API-KEY: ${API_KEY}")

    local count=$(echo $inactive | jq -r '. | length')
    echo "  Contacts inactifs (180j) : $count"

    if [ $count -gt 1000 ]; then
        echo "  ⚠️  Trop de contacts inactifs ($count) → Nettoyage recommandé"
        send_alert "Contacts inactifs : $count" "Recommandation : purger contacts inactifs > 180 jours"
    fi
}

# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════

# 1. Récupérer liste IPs via API
echo "1. Récupération liste IPs..."
IPS=$(curl -s "${API_URL}/api/v1/ips" -H "X-API-KEY: ${API_KEY}" | jq -r '.[].ip')

if [ -z "$IPS" ]; then
    echo "❌ Erreur : Impossible de récupérer liste IPs"
    exit 1
fi

IP_COUNT=$(echo "$IPS" | wc -l)
echo "  → $IP_COUNT IPs à vérifier"
echo ""

# 2. Check RBL pour chaque IP
echo "2. Check RBL (blacklist)..."
BLACKLISTED_COUNT=0
for ip in $IPS; do
    check_rbl "$ip"
    if [ $? -eq 1 ]; then
        BLACKLISTED_COUNT=$((BLACKLISTED_COUNT + 1))
    fi
    sleep 1  # Rate limiting DNS queries
done
echo ""

if [ $BLACKLISTED_COUNT -gt 0 ]; then
    echo "⚠️  $BLACKLISTED_COUNT IP(s) blacklistée(s)"
else
    echo "✅ Aucune IP blacklistée"
fi
echo ""

# 3. Check reputation score
echo "3. Check reputation score..."
for ip in $IPS; do
    echo "  IP: $ip"
    check_reputation "$ip"
done
echo ""

# 4. List hygiene
clean_bounces

# 5. Engagement tracking
clean_inactive

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  ✅ MONITORING TERMINÉ"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "Résumé :"
echo "  • IPs vérifiées : $IP_COUNT"
echo "  • IPs blacklistées : $BLACKLISTED_COUNT"
echo ""
echo "Prochaine exécution : dans 1 heure (cron)"
echo ""
