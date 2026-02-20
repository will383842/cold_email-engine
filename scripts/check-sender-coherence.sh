#!/bin/bash
################################################################################
# CHECK COHÉRENCE RUNTIME - Sur serveur VPS1
# Compare DB MailWizz (delivery servers) vs config PowerMTA live sur VPS2
# Alerte + pause si incohérence détectée
################################################################################

# Configuration
DB_NAME="${DB_NAME:-mailwizz_v2}"
DB_USER="${DB_USER:-mailwizz}"
DB_PASS="${DB_PASS}"
VPS2_IP="${PMTA_SSH_HOST}"
SSH_KEY="${PMTA_SSH_KEY_PATH:-/app/secrets/pmta_ssh_key}"
API_URL="${API_URL:-http://localhost:8000}"
API_KEY="${API_KEY}"
SLACK_WEBHOOK="${SLACK_WEBHOOK}"

ERRORS=0

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  CHECK COHÉRENCE RUNTIME"
echo "  MailWizz DB ↔ PowerMTA config live"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "═══════════════════════════════════════════════════════════"
echo ""

# ═══════════════════════════════════════════════════════════
# 1. LIRE delivery servers depuis MailWizz DB
# ═══════════════════════════════════════════════════════════
echo "1. Lecture delivery servers MailWizz (base de données)..."

MW_SENDERS=$(mysql -u "$DB_USER" -p"$DB_PASS" "$DB_NAME" -N -e \
    "SELECT from_email FROM mw_delivery_server WHERE status='active' ORDER BY id;" \
    2>/dev/null)

if [ -z "$MW_SENDERS" ]; then
    echo "   ❌ Impossible de lire la DB MailWizz (pas encore installé ?)"
    echo "   → Vérification ignorée"
    exit 0
fi

MW_COUNT=$(echo "$MW_SENDERS" | wc -l)
echo "   Delivery servers actifs : $MW_COUNT"
while IFS= read -r s; do
    echo "   - $s"
done <<< "$MW_SENDERS"

echo ""

# ═══════════════════════════════════════════════════════════
# 2. LIRE pattern-list depuis PowerMTA sur VPS2
# ═══════════════════════════════════════════════════════════
echo "2. Lecture pattern-list PowerMTA (config live sur VPS2)..."

if [ ! -f "$SSH_KEY" ]; then
    echo "   ❌ Clé SSH non trouvée : $SSH_KEY"
    echo "   → Vérification PowerMTA ignorée"
else
    PMTA_SENDERS=$(ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "root@$VPS2_IP" \
        "sed -n '/<pattern-list sender-to-vmta>/,/<\/pattern-list>/p' /etc/pmta/config | grep '@' | awk '{print \$1}'" \
        2>/dev/null)

    if [ -z "$PMTA_SENDERS" ]; then
        echo "   ❌ Impossible de lire la config PowerMTA"
    else
        PMTA_COUNT=$(echo "$PMTA_SENDERS" | wc -l)
        echo "   Senders dans pattern-list : $PMTA_COUNT"
        while IFS= read -r s; do
            echo "   - $s"
        done <<< "$PMTA_SENDERS"

        echo ""

        # ═══════════════════════════════════════════════════════════
        # 3. COMPARAISON
        # ═══════════════════════════════════════════════════════════
        echo "3. Comparaison..."
        echo ""
        printf "   %-42s %-42s %-8s\n" "MailWizz DB" "PowerMTA Config" "STATUS"
        printf "   %-42s %-42s %-8s\n" "──────────────────────────────────────────" "──────────────────────────────────────────" "────────"

        # Vérifier chaque sender MailWizz dans PowerMTA
        while IFS= read -r mw_sender; do
            if echo "$PMTA_SENDERS" | grep -qx "$mw_sender"; then
                printf "   %-42s %-42s %-8s\n" "$mw_sender" "$mw_sender" "✅ OK"
            else
                printf "   %-42s %-42s %-8s\n" "$mw_sender" "❌ MANQUANT" "❌ DIFF"
                ERRORS=$((ERRORS + 1))
            fi
        done <<< "$MW_SENDERS"

        # Vérifier chaque sender PowerMTA dans MailWizz
        while IFS= read -r pmta_sender; do
            if ! echo "$MW_SENDERS" | grep -qx "$pmta_sender"; then
                printf "   %-42s %-42s %-8s\n" "❌ MANQUANT" "$pmta_sender" "❌ DIFF"
                ERRORS=$((ERRORS + 1))
            fi
        done <<< "$PMTA_SENDERS"
    fi
fi

echo ""

# ═══════════════════════════════════════════════════════════
# 4. RÉSULTAT + ACTIONS
# ═══════════════════════════════════════════════════════════

if [ $ERRORS -gt 0 ]; then
    MSG="🚨 INCOHÉRENCE MailWizz↔PowerMTA : $ERRORS différence(s) détectée(s)\n"
    MSG+="MailWizz enverrait via la mauvaise IP → risque blacklist immédiat\n"
    MSG+="Action : corriger et redéployer"

    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║  🚨 INCOHÉRENCE DÉTECTÉE — ACTIONS PRISES                ║"
    echo "╠═══════════════════════════════════════════════════════════╣"
    echo "║                                                           ║"
    printf "║  Erreurs : %d                                             ║\n" "$ERRORS"
    echo "║                                                           ║"
    echo "║  CONSÉQUENCES si non corrigé :                           ║"
    echo "║  → MailWizz utilise mauvaise IP pour certains emails     ║"
    echo "║  → Warmup faussé (quota dépassé sur mauvaise IP)         ║"
    echo "║  → Réputation incorrecte                                  ║"
    echo "║  → Risque blacklist                                       ║"
    echo "║                                                           ║"
    echo "║  ACTIONS AUTOMATIQUES :                                   ║"
    echo "║  1. Pause des delivery servers incohérents                ║"
    echo "║  2. Alerte Slack/Email envoyée                            ║"
    echo "║  3. Logs dans /var/log/email-engine/coherence.log        ║"
    echo "║                                                           ║"
    echo "║  CORRECTION MANUELLE REQUISE :                           ║"
    echo "║  → Vérifier deploy/vps1-mailwizz/install.sh SENDER1-5    ║"
    echo "║  → Vérifier deploy/vps2-pmta/install.sh pattern-list     ║"
    echo "║  → Relancer : ./deploy/validate-coherence.sh             ║"
    echo "╚═══════════════════════════════════════════════════════════╝"

    # Pause delivery servers incohérents via API Email-Engine
    if [ ! -z "$API_KEY" ]; then
        echo ""
        echo "→ Pause delivery servers incohérents via API..."
        while IFS= read -r mw_sender; do
            if ! echo "$PMTA_SENDERS" | grep -qx "$mw_sender"; then
                curl -s -X PATCH "${API_URL}/api/v1/delivery-servers/pause" \
                    -H "X-API-KEY: ${API_KEY}" \
                    -H "Content-Type: application/json" \
                    -d "{\"from_email\": \"${mw_sender}\", \"reason\": \"Incohérence PowerMTA\"}" \
                    2>/dev/null || true
                echo "   Pausé : $mw_sender"
            fi
        done <<< "$MW_SENDERS"
    fi

    # Alerte Slack
    if [ ! -z "$SLACK_WEBHOOK" ]; then
        curl -s -X POST "$SLACK_WEBHOOK" \
            -H "Content-Type: application/json" \
            -d "{\"text\": \"${MSG}\"}" 2>/dev/null || true
    fi

    # Log
    mkdir -p /var/log/email-engine
    echo "$(date '+%Y-%m-%d %H:%M:%S') COHERENCE_ERROR errors=$ERRORS" \
        >> /var/log/email-engine/coherence.log

    exit 1
else
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║  ✅ COHÉRENCE PARFAITE                                    ║"
    echo "║                                                           ║"
    echo "║  MailWizz Delivery Servers = PowerMTA pattern-list       ║"
    echo "║  Chaque email sera envoyé depuis la bonne IP              ║"
    echo "╚═══════════════════════════════════════════════════════════╝"

    mkdir -p /var/log/email-engine
    echo "$(date '+%Y-%m-%d %H:%M:%S') COHERENCE_OK senders=$MW_COUNT" \
        >> /var/log/email-engine/coherence.log

    exit 0
fi
