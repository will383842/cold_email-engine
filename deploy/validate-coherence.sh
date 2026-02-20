#!/bin/bash
################################################################################
# VALIDATION COHÉRENCE PRÉ-DÉPLOIEMENT
# Vérifie que la configuration est prête avant de lancer deploy-all.sh
#
# Architecture : 1 domaine racine = 1 IP = mail.DOMAIN = vmta-DOMAIN
#
# NOTE : Les emails expéditeurs (pattern-list) NE SONT PAS vérifiés ici
# car ils sont configurés APRÈS déploiement via l'interface Email-Engine.
# Cette validation vérifie uniquement l'infrastructure.
################################################################################

set -e

DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VPS2_INSTALL="${DEPLOY_DIR}/vps2-pmta/install.sh"
VPS1_INSTALL="${DEPLOY_DIR}/vps1-mailwizz/install.sh"

ERRORS=0
WARNINGS=0

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  VALIDATION PRÉ-DÉPLOIEMENT — EMAIL-ENGINE V2"
echo "  Architecture : 1 IP par domaine racine"
echo "═══════════════════════════════════════════════════════════"
echo ""

# ─────────────────────────────────────────────────────────
# Fonctions utilitaires
# ─────────────────────────────────────────────────────────
domain_slug() {
    echo "$1" | sed 's/\.[^.]*$//' | sed 's/\./-/g'
}

# ═══════════════════════════════════════════════════════════
# 1. VÉRIFICATION FICHIERS REQUIS
# ═══════════════════════════════════════════════════════════
echo "1. Vérification fichiers requis..."

check_file() {
    local FILE=$1
    local DESC=$2
    if [ ! -f "$FILE" ]; then
        echo "   ❌ MANQUANT : $DESC"
        echo "      Chemin : $FILE"
        ERRORS=$((ERRORS + 1))
    else
        echo "   ✅ $DESC"
    fi
}

check_file "${DEPLOY_DIR}/vps1-mailwizz/install.sh"   "Script install MailWizz (VPS1)"
check_file "${DEPLOY_DIR}/vps2-pmta/install.sh"       "Script install PowerMTA (VPS2)"
check_file "${DEPLOY_DIR}/deploy-all.sh"              "Script déploiement global"
check_file "${DEPLOY_DIR}/dns-helper.sh"              "Script aide DNS"

# Fichiers mailwizz-email-engine
PROJECT_ROOT="$(dirname "$DEPLOY_DIR")"
MAILWIZZ_SOURCE="${PROJECT_ROOT}/mailwizz-email-engine"

check_file "${MAILWIZZ_SOURCE}/mailwizz-prod-20260216.tar.gz"  "Archive MailWizz"
check_file "${MAILWIZZ_SOURCE}/pmta-license-20260216"           "Licence PowerMTA"
check_file "${MAILWIZZ_SOURCE}/pmta-config-20260216"            "Config backup-cold PowerMTA"

echo ""

# ═══════════════════════════════════════════════════════════
# 2. EXTRACTION VARIABLES DEPUIS install.sh VPS2
# ═══════════════════════════════════════════════════════════
echo "2. Lecture configuration domaines/IPs (vps2-pmta/install.sh)..."

# Extraire DOMAIN_COUNT
DOMAIN_COUNT=$(grep '^DOMAIN_COUNT=' "$VPS2_INSTALL" | head -1 | sed 's/DOMAIN_COUNT=//;s/"//g;s/[^0-9].*$//')
DOMAIN_COUNT=${DOMAIN_COUNT:-5}
echo "   Nombre de domaines : $DOMAIN_COUNT"
echo ""

# Afficher tableau domaine/IP/vmta
printf "   %-5s %-30s %-20s %-25s %-12s\n" "N°" "Domaine" "IP" "mail.DOMAIN → vmta" "STATUS"
printf "   %-5s %-30s %-20s %-25s %-12s\n" "─────" "──────────────────────────────" "────────────────────" "─────────────────────────" "────────────"

for i in $(seq 1 $DOMAIN_COUNT); do
    DOMAIN_VAR="DOMAIN${i}"
    IP_VAR="IP${i}"

    # Extraire les valeurs des variables
    RAW_DOMAIN=$(grep "^DOMAIN${i}=" "$VPS2_INSTALL" | head -1 | sed 's/.*="\(.*\)".*/\1/')
    RAW_IP=$(grep "^IP${i}=" "$VPS2_INSTALL" | grep -v '#' | head -1 | sed 's/.*="\(.*\)".*/\1/' | awk '{print $1}')

    # Déduire slug et vmta
    SLUG=$(echo "$RAW_DOMAIN" | sed 's/\.[^.]*$//' | sed 's/\./-/g')
    VMTA="vmta-${SLUG}"
    MAIL_HOST="mail.${RAW_DOMAIN}"

    # Vérifier si placeholder
    if [[ "$RAW_DOMAIN" == *"domain"* ]] && [[ "$RAW_DOMAIN" == "domain"* ]]; then
        STATUS="⚠️ PLACEHOLDER"
        WARNINGS=$((WARNINGS + 1))
    elif [[ "$RAW_IP" == *"xxx"* ]] || [ -z "$RAW_IP" ]; then
        STATUS="❌ IP MANQUANTE"
        ERRORS=$((ERRORS + 1))
    else
        STATUS="✅ OK"
    fi

    printf "   %-5s %-30s %-20s %-25s %-12s\n" \
        "$i" "$RAW_DOMAIN" "$RAW_IP" "${MAIL_HOST}" "$STATUS"
done

echo ""

# ═══════════════════════════════════════════════════════════
# 3. VÉRIFICATION IPs — PAS DE DOUBLONS
# ═══════════════════════════════════════════════════════════
echo "3. Vérification unicité des IPs (isolation requise)..."

declare -A IP_SEEN
IP_DUPLICATES=0
for i in $(seq 1 $DOMAIN_COUNT); do
    RAW_IP=$(grep "^IP${i}=" "$VPS2_INSTALL" | grep -v '#' | head -1 | sed 's/.*="\(.*\)".*/\1/' | awk '{print $1}')
    if [[ "$RAW_IP" != *"xxx"* ]] && [ -n "$RAW_IP" ]; then
        if [ -n "${IP_SEEN[$RAW_IP]}" ]; then
            echo "   ❌ IP DUPLIQUÉE : $RAW_IP (domaine $i et ${IP_SEEN[$RAW_IP]})"
            IP_DUPLICATES=$((IP_DUPLICATES + 1))
            ERRORS=$((ERRORS + 1))
        else
            IP_SEEN["$RAW_IP"]=$i
        fi
    fi
done
if [ $IP_DUPLICATES -eq 0 ]; then
    echo "   ✅ Toutes les IPs sont uniques"
fi

echo ""

# ═══════════════════════════════════════════════════════════
# 4. VÉRIFICATION PMTA_HOST dans MailWizz install
# ═══════════════════════════════════════════════════════════
echo "4. Vérification PMTA_HOST (VPS1 → VPS2)..."

MW_PMTA_HOST=$(grep 'PMTA_HOST=' "$VPS1_INSTALL" | grep -v '#' | head -1 | sed 's/.*="\(.*\)".*/\1/')
if [ "$MW_PMTA_HOST" = "YOUR_VPS2_IP" ] || [ -z "$MW_PMTA_HOST" ]; then
    echo "   ⚠️  PMTA_HOST non configuré dans vps1-mailwizz/install.sh"
    echo "      Valeur actuelle : ${MW_PMTA_HOST:-vide}"
    echo "      Action : Remplacer YOUR_VPS2_IP par l'IP réelle de VPS2"
    WARNINGS=$((WARNINGS + 1))
else
    echo "   ✅ PMTA_HOST configuré : $MW_PMTA_HOST"
fi

echo ""

# ═══════════════════════════════════════════════════════════
# 5. VÉRIFICATION .env.production
# ═══════════════════════════════════════════════════════════
echo "5. Vérification .env.production..."

ENV_FILE="${PROJECT_ROOT}/.env.production"
if [ ! -f "$ENV_FILE" ]; then
    echo "   ❌ .env.production manquant"
    echo "      Action : cp .env.production.example .env.production"
    echo "               puis remplir les valeurs"
    ERRORS=$((ERRORS + 1))
else
    # Vérifier variables critiques
    check_env_var() {
        local KEY=$1
        local VAL=$(grep "^${KEY}=" "$ENV_FILE" | head -1 | cut -d'=' -f2- | tr -d '"')
        if [ -z "$VAL" ] || [[ "$VAL" == *"your_"* ]] || [[ "$VAL" == *"YOUR_"* ]] || [[ "$VAL" == *"changeme"* ]]; then
            echo "   ❌ ${KEY} non configuré"
            ERRORS=$((ERRORS + 1))
        else
            echo "   ✅ ${KEY} configuré"
        fi
    }

    check_env_var "API_KEY"
    check_env_var "PMTA_SSH_HOST"
    check_env_var "MAILWIZZ_API_URL"

    # PMTA_SSH_KEY_PATH
    SSH_KEY=$(grep "^PMTA_SSH_KEY_PATH=" "$ENV_FILE" | head -1 | cut -d'=' -f2- | tr -d '"' | awk '{print $1}')
    if [ -z "$SSH_KEY" ]; then
        SSH_KEY="/app/secrets/pmta_ssh_key"
    fi
    # Vérifier si la clé existe (chemin local, pas dans /app/ qui est Docker)
    LOCAL_SSH_KEY="${PROJECT_ROOT}/secrets/pmta_ssh_key"
    if [ -f "$LOCAL_SSH_KEY" ]; then
        echo "   ✅ Clé SSH PowerMTA présente : secrets/pmta_ssh_key"
    else
        echo "   ⚠️  Clé SSH PowerMTA absente : secrets/pmta_ssh_key"
        echo "      Elle sera générée par deploy-all.sh"
        WARNINGS=$((WARNINGS + 1))
    fi
fi

echo ""

# ═══════════════════════════════════════════════════════════
# 6. RAPPEL ARCHITECTURE (informationnel)
# ═══════════════════════════════════════════════════════════
echo "6. Architecture validée :"
echo ""
echo "   ┌─────────────────────────────────────────────────────┐"
echo "   │  APRÈS DÉPLOIEMENT — Configurer via interface :      │"
echo "   │                                                       │"
echo "   │  Pour chaque domaine, dans Email-Engine :            │"
echo "   │  POST /api/v1/ips  avec :                            │"
echo "   │    address      = IP (ex: 178.x.x.1)                │"
echo "   │    hostname     = mail.sos-holidays.com              │"
echo "   │    sender_email = contact@mail.sos-holidays.com (*)  │"
echo "   │                                                       │"
echo "   │  (*) Nom libre — ce n'est pas une vraie boîte mail   │"
echo "   │  L'API crée automatiquement :                        │"
echo "   │    1. virtual-mta PowerMTA (VPS2 via SSH)            │"
echo "   │    2. Delivery server MailWizz (même FROM email)     │"
echo "   └─────────────────────────────────────────────────────┘"

echo ""

# ═══════════════════════════════════════════════════════════
# RÉSULTAT FINAL
# ═══════════════════════════════════════════════════════════
if [ $ERRORS -gt 0 ]; then
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║                                                           ║"
    printf "║  🚫 VALIDATION ÉCHOUÉE — %d ERREUR(S) BLOQUANTE(S)      ║\n" "$ERRORS"
    echo "║                                                           ║"
    echo "║  Corriger les erreurs ci-dessus puis relancer :           ║"
    echo "║    ./deploy/validate-coherence.sh                        ║"
    echo "║    ./deploy/deploy-all.sh                                ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo ""
    exit 1
elif [ $WARNINGS -gt 0 ]; then
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║                                                           ║"
    printf "║  ⚠️  VALIDATION OK avec %d avertissement(s)              ║\n" "$WARNINGS"
    echo "║                                                           ║"
    echo "║  Les domaines sont encore des placeholders.              ║"
    echo "║  Vous pouvez déployer et configurer les vrais domaines   ║"
    echo "║  dans l'interface Email-Engine après déploiement.        ║"
    echo "║                                                           ║"
    echo "║  Déploiement autorisé (mode test/staging)                ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo ""
    exit 0
else
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║                                                           ║"
    echo "║  ✅ VALIDATION RÉUSSIE — Déploiement autorisé            ║"
    echo "║                                                           ║"
    echo "║  Tous les domaines, IPs et fichiers sont configurés.     ║"
    echo "║  Les emails expéditeurs seront ajoutés via l'interface.  ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo ""
    exit 0
fi
