#!/bin/bash
################################################################################
# INSTALLATION POWERMTA - VPS2 (Cloud VPS 10 Contabo)
# Domaines : hub-travelers.com + emilia-mullerd.com
#
# Architecture : 2 domaines × 1 IP dédiée = 2 virtual-mta
#   hub-travelers.com  → IP incluse VPS2  → mail.hub-travelers.com  → vmta-hub-travelers
#   emilia-mullerd.com → IP additionnelle → mail.emilia-mullerd.com → vmta-emilia-mullerd
#
# VPS3 (plane-liberty.com + planevilain.com) = installation identique
# → utiliser deploy/vps3-pmta/install.sh
################################################################################

set -e

echo "═══════════════════════════════════════════════════════════"
echo "  INSTALLATION POWERMTA - VPS2"
echo "  Domaines : hub-travelers.com + emilia-mullerd.com"
echo "═══════════════════════════════════════════════════════════"
echo ""

# ═══════════════════════════════════════════════════════════
# VARIABLES — À modifier avec tes vraies IPs Contabo VPS2
# ═══════════════════════════════════════════════════════════
DOMAIN_COUNT="${DOMAIN_COUNT:-2}"

DOMAIN1="${DOMAIN1:-hub-travelers.com}"    ; IP1="${IP1:-VPS2_IP_INCLUSE}"
DOMAIN2="${DOMAIN2:-emilia-mullerd.com}"   ; IP2="${IP2:-VPS2_IP_ADDITIONNELLE}"

POSTMASTER="${POSTMASTER:-admin@${DOMAIN1}}"

# ─────────────────────────────────────────────────────────
# Fonctions utilitaires
# ─────────────────────────────────────────────────────────
domain_slug() {
    echo "$1" | sed 's/\.[^.]*$//' | sed 's/\./-/g'
}

domain_to_vmta() {
    echo "vmta-$(domain_slug $1)"
}

echo "Configuration VPS2 :"
for i in $(seq 1 $DOMAIN_COUNT); do
    eval "D=\$DOMAIN${i}"
    eval "IP=\$IP${i}"
    echo "  ${i}. mail.${D}  →  ${IP}  [$(domain_to_vmta $D)]"
done
echo ""

# ═══════════════════════════════════════════════════════════
# 1. MISE À JOUR SYSTÈME
# ═══════════════════════════════════════════════════════════
echo "✓ Étape 1/7 : Mise à jour système..."
yum update -y 2>/dev/null || (apt update && apt upgrade -y)
echo "   ✅ Système à jour"

# ═══════════════════════════════════════════════════════════
# 2. LICENCE POWERMTA
# ═══════════════════════════════════════════════════════════
echo "✓ Étape 2/7 : Installation licence PowerMTA..."

if [ ! -f /tmp/pmta-license ]; then
    echo "❌ ERREUR : Licence PowerMTA manquante !"
    echo "   Upload requis :"
    echo "   scp pmta-license root@VPS2_IP:/tmp/pmta-license"
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
    echo "❌ ERREUR : PowerMTA RPM/DEB manquant !"
    echo "   Upload requis : scp powermta-5.0r*.rpm root@VPS2_IP:/tmp/"
    exit 1
fi
echo "   ✅ PowerMTA installé"

# ═══════════════════════════════════════════════════════════
# 4. GÉNÉRATION CLÉS DKIM (1 par domaine racine — 2048 bits)
# ═══════════════════════════════════════════════════════════
echo "✓ Étape 4/7 : Génération clés DKIM ($DOMAIN_COUNT domaines)..."
mkdir -p /etc/pmta/dkim

for i in $(seq 1 $DOMAIN_COUNT); do
    eval "DOMAIN=\$DOMAIN${i}"
    SLUG=$(domain_slug "$DOMAIN")
    DKIM_FILE="/etc/pmta/dkim/${SLUG}.pem"

    echo "   - Clé DKIM pour ${DOMAIN}"
    openssl genrsa -out "$DKIM_FILE" 2048 2>/dev/null
    chmod 600 "$DKIM_FILE"

    # Clé publique (1 ligne, sans headers PEM)
    openssl rsa -in "$DKIM_FILE" -pubout -outform PEM 2>/dev/null | \
        grep -v "PUBLIC KEY" | \
        tr -d '\n' > "/etc/pmta/dkim/${SLUG}.pub.txt"

    echo "     → Privée  : $DKIM_FILE"
    echo "     → Publique: /etc/pmta/dkim/${SLUG}.pub.txt"
done
echo "   ✅ $DOMAIN_COUNT clés DKIM générées"

# ═══════════════════════════════════════════════════════════
# 5. CONFIGURATION POWERMTA
# ═══════════════════════════════════════════════════════════
echo "✓ Étape 5/7 : Configuration PowerMTA..."

if [ -f /tmp/pmta-config-20260216 ]; then
    echo "   → Utilisation config backup-cold (règles ISP préservées)"
    cp /tmp/pmta-config-20260216 /etc/pmta/config

    # Remplacer l'ancien postmaster et hostname par les nouveaux
    sed -i "s|postmaster .*|postmaster ${POSTMASTER}|g" /etc/pmta/config
    sed -i "s|host-name .*|host-name mail.${DOMAIN1}|g" /etc/pmta/config

    sed -i '/<virtual-mta /,/<\/virtual-mta>/d' /etc/pmta/config
    sed -i '/<pattern-list /,/<\/pattern-list>/d' /etc/pmta/config
    sed -i '/virtual-mta-pool-map/d' /etc/pmta/config

    echo "   → Config adaptée (règles ISP/backoff conservées)"
else
    echo "   → Création config complète"
    cat > /etc/pmta/config <<EOF
################################################################################
# POWERMTA — VPS2 Email-Engine
# Domaines : hub-travelers.com + emilia-mullerd.com
# 1 IP par domaine racine — sender emails configurés via API après déploiement
################################################################################

postmaster ${POSTMASTER}
host-name mail.${DOMAIN1}

# SMTP Relay (reçoit depuis MailWizz sur VPS1)
# Port 2525 UNIQUEMENT depuis VPS1 (configurer firewall)
smtp-listener 0.0.0.0:2525 {
    listen-on-tcp yes
    process-x-virtual-mta yes
    process-x-sender yes
}

# ═══════════════════════════════════════════════════════════
# Logs
# ═══════════════════════════════════════════════════════════
log-file /var/log/pmta/log

<acct-file /var/log/pmta/acct.csv>
    max-size 100M
    records all
</acct-file>

spool /var/spool/pmta

# HTTP Management (localhost UNIQUEMENT)
http-mgmt-port 1983
http-access 127.0.0.1 admin

# ═══════════════════════════════════════════════════════════
# Règles ISP (conservateur — warmup hyper-protecteur)
# ═══════════════════════════════════════════════════════════
<domain gmail.com>
    max-msg-rate 50/h
    max-smtp-out 5
    retry-after 15m
    max-msg-per-connection 10
</domain>

<domain outlook.com hotmail.com live.com>
    max-msg-rate 30/h
    max-smtp-out 3
    retry-after 30m
    max-msg-per-connection 5
</domain>

<domain yahoo.com yahoo.fr>
    max-msg-rate 40/h
    max-smtp-out 4
    retry-after 20m
    max-msg-per-connection 8
</domain>

<domain orange.fr>
    max-msg-rate 20/h
    max-smtp-out 2
    retry-after 60m
    max-msg-per-connection 5
</domain>

<domain sfr.fr free.fr laposte.net>
    max-msg-rate 15/h
    max-smtp-out 2
    retry-after 60m
    max-msg-per-connection 5
</domain>

EOF
fi

# ═══════════════════════════════════════════════════════════
# 6. VIRTUAL-MTAs (1 par domaine)
# ═══════════════════════════════════════════════════════════
echo "✓ Étape 6/7 : Génération virtual-mta ($DOMAIN_COUNT domaines)..."

cat >> /etc/pmta/config <<EOF

################################################################################
# VIRTUAL MTAs — VPS2 : hub-travelers.com + emilia-mullerd.com
# 1 IP dédiée par domaine = isolation complète de réputation
# Ajoutés par Email-Engine API — NE PAS MODIFIER MANUELLEMENT
################################################################################

EOF

for i in $(seq 1 $DOMAIN_COUNT); do
    eval "DOMAIN=\$DOMAIN${i}"
    eval "IP=\$IP${i}"
    SLUG=$(domain_slug "$DOMAIN")
    VMTA=$(domain_to_vmta "$DOMAIN")
    MAIL_HOST="mail.${DOMAIN}"
    DKIM_KEY="/etc/pmta/dkim/${SLUG}.pem"

    cat >> /etc/pmta/config <<EOF
# Domaine ${i} : ${DOMAIN}
<virtual-mta ${VMTA}>
    smtp-source-host ${MAIL_HOST} ${IP}
    domain-key ${DOMAIN},${MAIL_HOST},*,${DKIM_KEY}
    <domain *>
        max-cold-virtual-mta-msg 5/day
        max-msg-rate 3/h
        require-starttls yes
        retry-after 30m
        max-smtp-out 2
    </domain>
    <domain gmail.com>
        max-msg-rate 2/h
        max-smtp-out 1
    </domain>
    <domain outlook.com hotmail.com live.com>
        max-msg-rate 1/h
        max-smtp-out 1
        retry-after 60m
    </domain>
</virtual-mta>

EOF

    echo "   ✅ ${VMTA} : ${MAIL_HOST} → ${IP}"
done

# Pattern-list VIDE — remplie par Email-Engine API
cat >> /etc/pmta/config <<EOF
################################################################################
# ROUTING SENDER → VIRTUAL-MTA
# Géré dynamiquement par Email-Engine API (POST /api/v1/ips)
# Format : sender_email@mail.domain.com   vmta-domain
# NE PAS MODIFIER MANUELLEMENT
################################################################################

<pattern-list sender-to-vmta>
    # Entrées ajoutées automatiquement par Email-Engine API
    # Exemple : contact@mail.hub-travelers.com   vmta-hub-travelers
</pattern-list>

<domain *>
    virtual-mta-pool-map sender-to-vmta
</domain>

################################################################################
# END CONFIGURATION VPS2
################################################################################
EOF

echo "   ✅ pattern-list créée (vide — remplie via API après déploiement)"

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
# FIREWALL
# ═══════════════════════════════════════════════════════════
echo ""
echo "✓ Configuration firewall..."
VPS1_IP="${VPS1_IP:-0.0.0.0}"

if command -v ufw &>/dev/null; then
    ufw allow 22/tcp comment "SSH admin"
    ufw allow 25/tcp comment "SMTP sortant"
    if [ "$VPS1_IP" != "0.0.0.0" ]; then
        ufw allow from "$VPS1_IP" to any port 2525 proto tcp comment "SMTP relay VPS1"
        ufw deny 2525/tcp comment "Bloquer autres connexions SMTP relay"
    fi
    ufw --force enable
    echo "   ✅ Firewall UFW configuré"
elif command -v firewall-cmd &>/dev/null; then
    firewall-cmd --permanent --add-port=22/tcp
    firewall-cmd --permanent --add-port=25/tcp
    if [ "$VPS1_IP" != "0.0.0.0" ]; then
        firewall-cmd --permanent --add-rich-rule="rule family=ipv4 source address=${VPS1_IP} port port=2525 protocol=tcp accept"
    fi
    firewall-cmd --reload
    echo "   ✅ Firewalld configuré"
else
    echo "   ⚠️  Configurer manuellement le firewall :"
    echo "      iptables -A INPUT -p tcp --dport 2525 -s VPS1_IP -j ACCEPT"
    echo "      iptables -A INPUT -p tcp --dport 2525 -j DROP"
fi

# ═══════════════════════════════════════════════════════════
# RÉSUMÉ FINAL
# ═══════════════════════════════════════════════════════════
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  ✅ INSTALLATION POWERMTA VPS2 TERMINÉE"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "Virtual-MTAs configurés :"
for i in $(seq 1 $DOMAIN_COUNT); do
    eval "DOMAIN=\$DOMAIN${i}"
    eval "IP=\$IP${i}"
    VMTA=$(domain_to_vmta "$DOMAIN")
    echo "  ${i}. $(printf '%-30s' "mail.${DOMAIN}") → $(printf '%-18s' "${IP}")  [${VMTA}]"
done

echo ""
echo "Clés DKIM publiques (à copier dans DNS Cloudflare) :"
echo "─────────────────────────────────────────────────────────"
for i in $(seq 1 $DOMAIN_COUNT); do
    eval "DOMAIN=\$DOMAIN${i}"
    SLUG=$(domain_slug "$DOMAIN")
    echo ""
    echo "  ${DOMAIN} :"
    echo "    Nom    : mail._domainkey.mail.${DOMAIN}"
    echo "    Type   : TXT"
    echo "    Valeur : v=DKIM1; k=rsa; p=$(cat /etc/pmta/dkim/${SLUG}.pub.txt 2>/dev/null || echo '[ERREUR]')"
done

echo ""
echo "PROCHAINES ÉTAPES :"
echo "  1. Configurer DNS (voir dns-helper.sh)"
echo "  2. Ajouter clé SSH de VPS1 :"
echo "     ssh-copy-id -i secrets/pmta_ssh_key.pub root@VPS2_IP"
echo "  3. Configurer .env (VPS1) :"
echo "     PMTA_VPS2_HOST=$(hostname -I | awk '{print $1}')"
echo "     PMTA_VPS2_DOMAINS=hub-travelers.com,emilia-mullerd.com"
echo "  4. Ajouter IPs via Email-Engine API : POST /api/v1/ips"
echo ""
echo "═══════════════════════════════════════════════════════════"
