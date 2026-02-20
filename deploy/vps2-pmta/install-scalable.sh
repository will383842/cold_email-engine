#!/bin/bash
################################################################################
# INSTALLATION POWERMTA - VERSION SCALABLE (N domaines)
#
# Même architecture que install.sh mais scalable via variable DOMAIN_LIST
# Format : "domain1.com:IP1,domain2.com:IP2,..."
#
# Exemple pour 20 domaines :
#   export DOMAIN_LIST="sos-holidays.com:178.x.x.1,expat-guide.com:178.x.x.2,..."
#   ./install-scalable.sh
################################################################################

set -e

# ─────────────────────────────────────────────────────────
# Fonctions utilitaires
# ─────────────────────────────────────────────────────────
domain_slug() {
    echo "$1" | sed 's/\.[^.]*$//' | sed 's/\./-/g'
}

domain_to_vmta() {
    echo "vmta-$(domain_slug $1)"
}

# ─────────────────────────────────────────────────────────
# Lecture DOMAIN_LIST ou variables DOMAIN{N}/IP{N}
# ─────────────────────────────────────────────────────────
DOMAINS=()
IPS=()

if [ -n "$DOMAIN_LIST" ]; then
    # Format : "sos-holidays.com:178.x.x.1,expat-guide.com:178.x.x.2"
    IFS=',' read -ra PAIRS <<< "$DOMAIN_LIST"
    for PAIR in "${PAIRS[@]}"; do
        D=$(echo "$PAIR" | cut -d':' -f1 | tr -d ' ')
        I=$(echo "$PAIR" | cut -d':' -f2 | tr -d ' ')
        DOMAINS+=("$D")
        IPS+=("$I")
    done
else
    # Fallback : variables DOMAIN{N}/IP{N}
    COUNT="${DOMAIN_COUNT:-5}"
    for i in $(seq 1 $COUNT); do
        eval "D=\${DOMAIN${i}:-domain${i}.com}"
        eval "I=\${IP${i}:-178.xxx.xxx.${i}}"
        DOMAINS+=("$D")
        IPS+=("$I")
    done
fi

DOMAIN_COUNT="${#DOMAINS[@]}"
POSTMASTER="${POSTMASTER:-admin@${DOMAINS[0]}}"

echo "═══════════════════════════════════════════════════════════"
echo "  INSTALLATION POWERMTA — SCALABLE"
echo "  $DOMAIN_COUNT domaines, 1 IP par domaine"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "Configuration :"
for i in "${!DOMAINS[@]}"; do
    echo "  $((i+1)). mail.${DOMAINS[$i]}  →  ${IPS[$i]}"
done
echo ""

# ═══════════════════════════════════════════════════════════
# 1. MISE À JOUR SYSTÈME
# ═══════════════════════════════════════════════════════════
echo "✓ Étape 1/7 : Mise à jour système..."
yum update -y 2>/dev/null || (apt update && apt upgrade -y)

# ═══════════════════════════════════════════════════════════
# 2. LICENCE POWERMTA
# ═══════════════════════════════════════════════════════════
echo "✓ Étape 2/7 : Installation licence PowerMTA..."
if [ ! -f /tmp/pmta-license ]; then
    echo "❌ Licence PowerMTA manquante (/tmp/pmta-license)"
    exit 1
fi
mkdir -p /etc/pmta
cp /tmp/pmta-license /etc/pmta/license
chmod 644 /etc/pmta/license
echo "   ✅ Licence installée"

# ═══════════════════════════════════════════════════════════
# 3. INSTALLATION POWERMTA
# ═══════════════════════════════════════════════════════════
echo "✓ Étape 3/7 : Installation PowerMTA..."
if ls /tmp/powermta-*.rpm 1>/dev/null 2>&1; then
    rpm -ivh /tmp/powermta-*.rpm
elif ls /tmp/powermta-*.deb 1>/dev/null 2>&1; then
    dpkg -i /tmp/powermta-*.deb
else
    echo "❌ PowerMTA RPM/DEB manquant"
    exit 1
fi
echo "   ✅ PowerMTA installé"

# ═══════════════════════════════════════════════════════════
# 4. GÉNÉRATION CLÉS DKIM (1 par domaine)
# ═══════════════════════════════════════════════════════════
echo "✓ Étape 4/7 : Génération $DOMAIN_COUNT clés DKIM..."
mkdir -p /etc/pmta/dkim

for i in "${!DOMAINS[@]}"; do
    DOMAIN="${DOMAINS[$i]}"
    SLUG=$(domain_slug "$DOMAIN")
    DKIM_FILE="/etc/pmta/dkim/${SLUG}.pem"

    openssl genrsa -out "$DKIM_FILE" 2048 2>/dev/null
    chmod 600 "$DKIM_FILE"
    openssl rsa -in "$DKIM_FILE" -pubout -outform PEM 2>/dev/null | \
        grep -v "PUBLIC KEY" | tr -d '\n' > "/etc/pmta/dkim/${SLUG}.pub.txt"

    echo "   ✅ ${DOMAIN} → /etc/pmta/dkim/${SLUG}.pem"
done

# ═══════════════════════════════════════════════════════════
# 5. CONFIGURATION DE BASE POWERMTA
# ═══════════════════════════════════════════════════════════
echo "✓ Étape 5/7 : Configuration PowerMTA..."

if [ -f /tmp/pmta-config-20260216 ]; then
    cp /tmp/pmta-config-20260216 /etc/pmta/config
    sed -i "s|postmaster .*|postmaster ${POSTMASTER}|g" /etc/pmta/config
    sed -i "s|host-name .*|host-name mail.${DOMAINS[0]}|g" /etc/pmta/config
    sed -i '/<virtual-mta /,/<\/virtual-mta>/d' /etc/pmta/config
    sed -i '/<pattern-list /,/<\/pattern-list>/d' /etc/pmta/config
    sed -i '/virtual-mta-pool-map/d' /etc/pmta/config
    echo "   ✅ Config backup-cold adaptée (règles ISP préservées)"
else
    cat > /etc/pmta/config <<EOF
################################################################################
# POWERMTA — EMAIL-ENGINE V2 SCALABLE
# $DOMAIN_COUNT domaines, 1 IP par domaine
################################################################################

postmaster ${POSTMASTER}
host-name mail.${DOMAINS[0]}

smtp-listener 0.0.0.0:2525 {
    listen-on-tcp yes
    process-x-virtual-mta yes
    process-x-sender yes
}

log-file /var/log/pmta/log

<acct-file /var/log/pmta/acct.csv>
    max-size 100M
    records all
</acct-file>

spool /var/spool/pmta
http-mgmt-port 1983
http-access 127.0.0.1 admin

<domain gmail.com>
    max-msg-rate 50/h
    max-smtp-out 5
    retry-after 15m
</domain>

<domain outlook.com hotmail.com live.com>
    max-msg-rate 30/h
    max-smtp-out 3
    retry-after 30m
</domain>

<domain yahoo.com yahoo.fr>
    max-msg-rate 40/h
    max-smtp-out 4
    retry-after 20m
</domain>

<domain orange.fr sfr.fr free.fr>
    max-msg-rate 15/h
    max-smtp-out 2
    retry-after 60m
</domain>

EOF
fi

# ═══════════════════════════════════════════════════════════
# 6. VIRTUAL-MTAs + PATTERN-LIST (dynamique)
# ═══════════════════════════════════════════════════════════
echo "✓ Étape 6/7 : Génération $DOMAIN_COUNT virtual-mta..."

cat >> /etc/pmta/config <<EOF

################################################################################
# VIRTUAL MTAs — $DOMAIN_COUNT domaines, 1 IP par domaine
# Généré automatiquement par install-scalable.sh
################################################################################

EOF

for i in "${!DOMAINS[@]}"; do
    DOMAIN="${DOMAINS[$i]}"
    IP="${IPS[$i]}"
    SLUG=$(domain_slug "$DOMAIN")
    VMTA=$(domain_to_vmta "$DOMAIN")
    MAIL_HOST="mail.${DOMAIN}"
    DKIM_KEY="/etc/pmta/dkim/${SLUG}.pem"

    cat >> /etc/pmta/config <<EOF
# Domaine $((i+1)) : ${DOMAIN}
<virtual-mta ${VMTA}>
    smtp-source-host ${MAIL_HOST} ${IP}
    domain-key ${DOMAIN},${MAIL_HOST},*,${DKIM_KEY}
    <domain *>
        max-cold-virtual-mta-msg 50/day
        max-msg-rate 100/h
        require-starttls yes
    </domain>
</virtual-mta>

EOF
    echo "   ✅ ${VMTA} : ${MAIL_HOST} → ${IP}"
done

# Pattern-list vide — remplie par Email-Engine API
cat >> /etc/pmta/config <<EOF
################################################################################
# ROUTING SENDER → VIRTUAL-MTA
# Géré dynamiquement par Email-Engine API
# Ajouté via : POST /api/v1/ips (avec sender_email)
################################################################################

<pattern-list sender-to-vmta>
    # Entrées ajoutées automatiquement par Email-Engine API
</pattern-list>

<domain *>
    virtual-mta-pool-map sender-to-vmta
</domain>

################################################################################
# END CONFIGURATION
################################################################################
EOF

# ═══════════════════════════════════════════════════════════
# 7. DÉMARRAGE POWERMTA
# ═══════════════════════════════════════════════════════════
echo "✓ Étape 7/7 : Démarrage PowerMTA..."
systemctl enable pmta
systemctl start pmta
sleep 3

if systemctl is-active --quiet pmta; then
    echo "   ✅ PowerMTA démarré"
else
    echo "   ❌ PowerMTA ne démarre pas — vérifier : journalctl -u pmta"
    exit 1
fi

# ═══════════════════════════════════════════════════════════
# RÉSUMÉ
# ═══════════════════════════════════════════════════════════
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  ✅ INSTALLATION TERMINÉE — $DOMAIN_COUNT domaines"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "Pour ajouter plus de domaines plus tard :"
echo "  export DOMAIN_LIST=\"nouveaudomaine.com:178.x.x.N,...\""
echo "  ./install-scalable.sh"
echo ""
echo "Pour configurer les emails expéditeurs :"
echo "  Ouvrir Email-Engine API → POST /api/v1/ips"
echo "  avec address, hostname (mail.DOMAIN) et sender_email"
echo ""
echo "Clés DKIM publiques (à ajouter dans DNS) :"
for i in "${!DOMAINS[@]}"; do
    DOMAIN="${DOMAINS[$i]}"
    SLUG=$(domain_slug "$DOMAIN")
    echo ""
    echo "  ${DOMAIN} :"
    echo "    Nom : mail._domainkey.mail.${DOMAIN}"
    echo "    TXT : v=DKIM1; k=rsa; p=$(cat /etc/pmta/dkim/${SLUG}.pub.txt 2>/dev/null || echo '[ERREUR]')"
done
echo ""
echo "═══════════════════════════════════════════════════════════"
