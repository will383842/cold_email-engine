#!/bin/bash
################################################################################
# DNS CONFIGURATION HELPER - EMAIL-ENGINE V2
# Génère tous les records DNS pour N domaines racines
#
# Architecture : 1 domaine racine = 1 IP = 1 sous-domaine mail.DOMAIN
#
# DNS nécessaire par domaine :
#   mail.DOMAIN     A      IP           (sous-domaine envoi)
#   mail.DOMAIN     TXT    v=spf1 ...   (SPF)
#   mail._domainkey.mail.DOMAIN  TXT  DKIM
#   _dmarc.mail.DOMAIN  TXT  DMARC
#   PTR  IP → mail.DOMAIN              (chez hébergeur VPS)
#   Redirection email admin@DOMAIN → ton_email (Cloudflare gratuit)
################################################################################

set -e

# ═══════════════════════════════════════════════════════════
# VARIABLES (identiques à install.sh VPS2)
# ═══════════════════════════════════════════════════════════
DOMAIN_COUNT="${DOMAIN_COUNT:-4}"

# Remplace CONTABO_IP_X par tes vraies IPs
DOMAIN1="${DOMAIN1:-hub-travelers.com}"   ; IP1="${IP1:-CONTABO_IP_1}"
DOMAIN2="${DOMAIN2:-emilia-mullerd.com}"  ; IP2="${IP2:-CONTABO_IP_2}"
DOMAIN3="${DOMAIN3:-plane-liberty.com}"   ; IP3="${IP3:-CONTABO_IP_3}"
DOMAIN4="${DOMAIN4:-planevilain.com}"     ; IP4="${IP4:-CONTABO_IP_4}"

# Clés DKIM (générées sur VPS2 Contabo par install.sh)
DKIM_PATH="${DKIM_PATH:-/etc/pmta/dkim}"

# Ton vrai email (boîte Gmail/Zoho — 1 seule pour tous les domaines)
YOUR_REAL_EMAIL="${YOUR_REAL_EMAIL:-ton_email@gmail.com}"

# ─────────────────────────────────────────────────────────
# Fonctions utilitaires (identiques à install.sh)
# ─────────────────────────────────────────────────────────
domain_slug() {
    echo "$1" | sed 's/\.[^.]*$//' | sed 's/\./-/g'
}

# ─────────────────────────────────────────────────────────
# Génération records DNS pour un domaine
# ─────────────────────────────────────────────────────────
generate_dns_records() {
    local DOMAIN=$1
    local IP=$2
    local SLUG=$(domain_slug "$DOMAIN")
    local MAIL_HOST="mail.${DOMAIN}"
    local DKIM_FILE="${DKIM_PATH}/${SLUG}.pub.txt"

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  DOMAINE : ${DOMAIN}"
    echo "  Sous-domaine envoi : ${MAIL_HOST}  →  ${IP}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    # 1. A RECORD
    echo "  ✓ A RECORD (sous-domaine envoi → IP dédiée)"
    echo "    Nom    : ${MAIL_HOST}"
    echo "    Type   : A"
    echo "    Valeur : ${IP}"
    echo "    TTL    : 3600"
    echo ""

    # 2. SPF RECORD
    echo "  ✓ SPF RECORD (autoriser cette IP à envoyer)"
    echo "    Nom    : ${MAIL_HOST}"
    echo "    Type   : TXT"
    echo "    Valeur : \"v=spf1 ip4:${IP} -all\""
    echo "    TTL    : 3600"
    echo ""

    # 3. DKIM RECORD
    echo "  ✓ DKIM RECORD (signature cryptographique)"
    echo "    Nom    : mail._domainkey.${MAIL_HOST}"
    echo "    Type   : TXT"
    if [ -f "$DKIM_FILE" ]; then
        DKIM_KEY=$(cat "$DKIM_FILE")
        echo "    Valeur : \"v=DKIM1; k=rsa; p=${DKIM_KEY}\""
    else
        echo "    Valeur : [COPIER depuis VPS2 : cat ${DKIM_PATH}/${SLUG}.pub.txt]"
        echo "    Note   : Généré par install.sh VPS2 — récupérer avec scp ou deploy-all.sh"
    fi
    echo "    TTL    : 3600"
    echo ""

    # 4. DMARC RECORD
    echo "  ✓ DMARC RECORD (politique anti-spoofing)"
    echo "    Nom    : _dmarc.${MAIL_HOST}"
    echo "    Type   : TXT"
    echo "    Valeur : \"v=DMARC1; p=quarantine; rua=mailto:admin@${DOMAIN}; pct=100; adkim=s; aspf=s\""
    echo "    TTL    : 3600"
    echo ""

    # 5. PTR RECORD
    echo "  ✓ PTR RECORD / REVERSE DNS (à configurer chez ton hébergeur VPS)"
    echo "    IP     : ${IP}"
    echo "    PTR    : ${MAIL_HOST}"
    echo "    Action : Contacter hébergeur VPS (Hetzner/OVH/etc.)"
    echo "             → Demander PTR pour IP ${IP} → ${MAIL_HOST}"
    echo ""

    # 6. EMAIL REDIRECTION (postmaster — via Cloudflare gratuit)
    echo "  ✓ REDIRECTION EMAIL (postmaster — via Cloudflare gratuit)"
    echo "    De  : admin@${DOMAIN}"
    echo "    Vers: ${YOUR_REAL_EMAIL}"
    echo "    Via : Cloudflare > Email > Email Routing > Add address"
    echo "    Note: 1 seule vraie boîte mail pour tous tes domaines"
    echo ""
}

# ═══════════════════════════════════════════════════════════
# GÉNÉRATION POUR TOUS LES DOMAINES
# ═══════════════════════════════════════════════════════════
echo "═══════════════════════════════════════════════════════════"
echo "  DNS CONFIGURATION — EMAIL-ENGINE V2"
echo "  Architecture : 1 IP par domaine racine"
echo "═══════════════════════════════════════════════════════════"

for i in $(seq 1 $DOMAIN_COUNT); do
    eval "DOMAIN=\$DOMAIN${i}"
    eval "IP=\$IP${i}"
    generate_dns_records "$DOMAIN" "$IP"
done

# ═══════════════════════════════════════════════════════════
# VÉRIFICATIONS DNS POST-CONFIGURATION
# ═══════════════════════════════════════════════════════════
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  VÉRIFICATIONS (après propagation DNS 24-48h)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

for i in $(seq 1 $DOMAIN_COUNT); do
    eval "DOMAIN=\$DOMAIN${i}"
    eval "IP=\$IP${i}"
    SLUG=$(domain_slug "$DOMAIN")
    MAIL_HOST="mail.${DOMAIN}"
    echo "  ${DOMAIN} :"
    echo "    dig A ${MAIL_HOST} +short                          → doit retourner ${IP}"
    echo "    dig TXT ${MAIL_HOST} +short                        → doit contenir spf1"
    echo "    dig TXT mail._domainkey.${MAIL_HOST} +short        → doit contenir DKIM1"
    echo "    dig TXT _dmarc.${MAIL_HOST} +short                 → doit contenir DMARC1"
    echo "    dig -x ${IP} +short                                → doit retourner ${MAIL_HOST}"
    echo ""
done

echo "  Outil en ligne : https://mxtoolbox.com/SuperTool.aspx"
echo "  Test email     : mail-tester.com (score cible 10/10)"
echo ""

# ═══════════════════════════════════════════════════════════
# EXPORT CSV (pour import bulk dans panel DNS)
# ═══════════════════════════════════════════════════════════
CSV_FILE="dns_records_$(date +%Y%m%d_%H%M%S).csv"

{
echo "Type,Name,Value,TTL"
echo "# EMAIL-ENGINE V2 — DNS Records — $(date)"
echo "# 1 IP par domaine racine"
echo "#"

for i in $(seq 1 $DOMAIN_COUNT); do
    eval "DOMAIN=\$DOMAIN${i}"
    eval "IP=\$IP${i}"
    SLUG=$(domain_slug "$DOMAIN")
    MAIL_HOST="mail.${DOMAIN}"

    # Lire clé DKIM si disponible
    if [ -f "${DKIM_PATH}/${SLUG}.pub.txt" ]; then
        DKIM_KEY="v=DKIM1; k=rsa; p=$(cat ${DKIM_PATH}/${SLUG}.pub.txt)"
    else
        DKIM_KEY="v=DKIM1; k=rsa; p=[COPIER_CLE_DEPUIS_VPS2_/etc/pmta/dkim/${SLUG}.pub.txt]"
    fi

    echo ""
    echo "# ${DOMAIN}"
    echo "A,${MAIL_HOST},${IP},3600"
    echo "TXT,${MAIL_HOST},\"v=spf1 ip4:${IP} -all\",3600"
    echo "TXT,mail._domainkey.${MAIL_HOST},\"${DKIM_KEY}\",3600"
    echo "TXT,_dmarc.${MAIL_HOST},\"v=DMARC1; p=quarantine; rua=mailto:admin@${DOMAIN}; pct=100; adkim=s; aspf=s\",3600"
    echo "# PTR: ${IP} → ${MAIL_HOST}  (à configurer chez hébergeur VPS)"
done
} > "$CSV_FILE"

echo "═══════════════════════════════════════════════════════════"
echo "  ✅ Fichier CSV généré : ${CSV_FILE}"
echo "  (importer dans ton panel DNS ou Cloudflare)"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "RAPPEL : Les noms d'emails expéditeurs"
echo "  (ex: contact@mail.sos-holidays.com)"
echo "  se configurent APRÈS dans l'interface Email-Engine."
echo "  Aucune boîte email physique nécessaire."
echo ""
