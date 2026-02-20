#!/bin/bash
################################################################################
# INSTALLATION MAILWIZZ - VPS1
# Système : MailWizz vierge (base de données VIDE, pas d'import backup-cold)
#
# Architecture : 1 domaine racine = 1 IP = mail.DOMAIN
# Les delivery servers (emails expéditeurs) sont configurés APRÈS
# via l'interface Email-Engine API — PAS hardcodés ici.
################################################################################

set -e  # Exit on error

echo "═══════════════════════════════════════════════════════════"
echo "  INSTALLATION MAILWIZZ - VPS1"
echo "  Base de données VIDE (système neuf)"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Variables
# sos-holidays.com = domaine de l'interface MailWizz (Hetzner CPX32 / O2switch)
# Ce N'EST PAS un domaine d'envoi — c'est le panneau d'administration
DOMAIN="sos-holidays.com"
EMAIL="admin@sos-holidays.com"
DB_NAME="mailwizz_v2"
DB_USER="mailwizz"
DB_PASS=$(openssl rand -base64 32)

# ─────────────────────────────────────────────────────────
# VPS2 PowerMTA - connexion SMTP
# Les delivery servers (emails expéditeurs) sont créés via l'API
# après déploiement, pas hardcodés ici.
# ─────────────────────────────────────────────────────────
PMTA_HOST="${PMTA_SSH_HOST:-YOUR_VPS2_IP}"   # IP du VPS2 PowerMTA
PMTA_PORT="${PMTA_SMTP_PORT:-2525}"

# ═══════════════════════════════════════════════════════════
# 1. MISE À JOUR SYSTÈME
# ═══════════════════════════════════════════════════════════
echo "✓ Étape 1/8 : Mise à jour système..."
apt update && apt upgrade -y

# ═══════════════════════════════════════════════════════════
# 2. INSTALLATION STACK LAMP
# ═══════════════════════════════════════════════════════════
echo "✓ Étape 2/8 : Installation LAMP stack..."
apt install -y \
    apache2 \
    mysql-server \
    php8.1 \
    php8.1-cli \
    php8.1-mysql \
    php8.1-mbstring \
    php8.1-xml \
    php8.1-curl \
    php8.1-zip \
    php8.1-gd \
    php8.1-intl \
    php8.1-imap \
    php8.1-bcmath \
    unzip \
    curl

# ═══════════════════════════════════════════════════════════
# 3. CONFIGURATION MYSQL
# ═══════════════════════════════════════════════════════════
echo "✓ Étape 3/8 : Configuration MySQL..."

# Base de données VIDE (pas d'import SQL)
# IMPORTANT : On n'importe PAS mailapp-prod-20260216.sql.gz
# → Pas de templates, segments, campagnes de backup-cold
# → Système neuf, vierge

mysql -e "CREATE DATABASE ${DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -e "CREATE USER '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASS}';"
mysql -e "GRANT ALL PRIVILEGES ON ${DB_NAME}.* TO '${DB_USER}'@'localhost';"
mysql -e "FLUSH PRIVILEGES;"

echo "Base MySQL créée : ${DB_NAME} (VIDE - pas d'import backup-cold)"
echo "Utilisateur MySQL : ${DB_USER}"
echo "Mot de passe MySQL : ${DB_PASS}" > /root/mysql_credentials.txt
chmod 600 /root/mysql_credentials.txt

# ═══════════════════════════════════════════════════════════
# 4. UPLOAD MAILWIZZ (depuis mailwizz-email-engine)
# ═══════════════════════════════════════════════════════════
echo "✓ Étape 4/8 : Vérification MailWizz archive..."

# Upload depuis local (à faire avant script)
# scp mailwizz-email-engine/mailwizz-prod-20260216.tar.gz root@VPS1:/tmp/

if [ ! -f /tmp/mailwizz-prod-20260216.tar.gz ]; then
    echo "❌ ERREUR : Archive MailWizz manquante !"
    echo "Upload requis : scp mailwizz-email-engine/mailwizz-prod-20260216.tar.gz root@${DOMAIN}:/tmp/"
    exit 1
fi

echo "✅ Archive MailWizz trouvée"

# ═══════════════════════════════════════════════════════════
# 5. INSTALLATION MAILWIZZ
# ═══════════════════════════════════════════════════════════
echo "✓ Étape 5/8 : Installation MailWizz..."
cd /var/www/html
rm -rf * 2>/dev/null || true

# Extraire depuis tar.gz (backup-cold)
tar -xzf /tmp/mailwizz-prod-20260216.tar.gz --strip-components=3 -C /var/www/html

chown -R www-data:www-data /var/www/html
chmod -R 755 /var/www/html

# Permissions spécifiques MailWizz
chmod -R 777 /var/www/html/apps/common/runtime
chmod -R 777 /var/www/html/apps/frontend/assets
chmod -R 777 /var/www/html/apps/backend/assets
chmod -R 777 /var/www/html/apps/customer/assets

# ═══════════════════════════════════════════════════════════
# 6. CONFIGURATION APACHE
# ═══════════════════════════════════════════════════════════
echo "✓ Étape 6/8 : Configuration Apache..."
cat > /etc/apache2/sites-available/${DOMAIN}.conf <<EOF
<VirtualHost *:80>
    ServerName ${DOMAIN}
    ServerAdmin ${EMAIL}
    DocumentRoot /var/www/html

    <Directory /var/www/html>
        Options -Indexes +FollowSymLinks
        AllowOverride All
        Require all granted
    </Directory>

    ErrorLog \${APACHE_LOG_DIR}/${DOMAIN}_error.log
    CustomLog \${APACHE_LOG_DIR}/${DOMAIN}_access.log combined
</VirtualHost>
EOF

# Activer site et modules
a2ensite ${DOMAIN}.conf
a2enmod rewrite
a2dissite 000-default.conf
systemctl restart apache2

# ═══════════════════════════════════════════════════════════
# 7. SSL AVEC CERTBOT
# ═══════════════════════════════════════════════════════════
echo "✓ Étape 7/8 : Installation SSL (Let's Encrypt)..."
apt install -y certbot python3-certbot-apache
certbot --apache -d ${DOMAIN} --non-interactive --agree-tos --email ${EMAIL} || echo "SSL config à faire manuellement"

# ═══════════════════════════════════════════════════════════
# 8. CONFIGURATION CRON MAILWIZZ + CHECKS
# ═══════════════════════════════════════════════════════════
echo "✓ Étape 8/8 : Configuration cron MailWizz + checks..."

# Crons MailWizz
(crontab -l 2>/dev/null; echo "* * * * * /usr/bin/php /var/www/html/apps/console/console.php send-campaigns >/dev/null 2>&1") | crontab -
(crontab -l 2>/dev/null; echo "*/5 * * * * /usr/bin/php /var/www/html/apps/console/console.php process-bounces >/dev/null 2>&1") | crontab -
(crontab -l 2>/dev/null; echo "*/5 * * * * /usr/bin/php /var/www/html/apps/console/console.php process-feedback-loop >/dev/null 2>&1") | crontab -

# Check cohérence MailWizz ↔ PowerMTA (toutes les heures)
(crontab -l 2>/dev/null; echo "0 * * * * /opt/email-engine/scripts/check-sender-coherence.sh >> /var/log/email-engine/coherence.log 2>&1") | crontab -

# Check blacklists (toutes les heures)
(crontab -l 2>/dev/null; echo "30 * * * * /opt/email-engine/scripts/blacklist-protection.sh >> /var/log/email-engine/blacklist.log 2>&1") | crontab -

mkdir -p /var/log/email-engine

# ═══════════════════════════════════════════════════════════
# 9. DELIVERY SERVERS — CONFIGURÉS VIA EMAIL-ENGINE API
# ═══════════════════════════════════════════════════════════
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  DELIVERY SERVERS : Configuration via interface"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  Les delivery servers MailWizz (emails expéditeurs)"
echo "  sont créés AUTOMATIQUEMENT par Email-Engine API."
echo ""
echo "  Flux : Interface → POST /api/v1/ips avec sender_email"
echo "    1. API crée virtual-mta dans PowerMTA (VPS2 via SSH)"
echo "    2. API crée delivery server dans MailWizz (même FROM)"
echo "    3. Cohérence garantie automatiquement"
echo ""
echo "  Pas de SQL à exécuter manuellement."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Générer une note de référence pour l'admin
cat > /root/delivery-servers-info.txt <<EOF
DELIVERY SERVERS MAILWIZZ — EMAIL-ENGINE V2
===========================================

Architecture : 1 domaine racine = 1 IP = 1 sous-domaine mail.DOMAIN

Les delivery servers sont créés automatiquement par Email-Engine API
quand vous ajoutez une IP via l'interface.

Exemple :
  POST http://VPS1:8000/api/v1/ips
  {
    "address": "178.x.x.1",
    "hostname": "mail.sos-holidays.com",
    "sender_email": "contact@mail.sos-holidays.com",
    "from_name": "SOS Holidays"
  }

L'API crée automatiquement :
  1. virtual-mta dans PowerMTA (VPS2)
  2. Delivery server dans MailWizz avec FROM = sender_email
  3. Entrée dans pattern-list PowerMTA

Pour vérifier les delivery servers créés :
  MailWizz Backend > Delivery Servers > Liste

PowerMTA SMTP : ${PMTA_HOST}:${PMTA_PORT}
EOF

chmod 600 /root/delivery-servers-info.txt
echo "✓ Note de référence : /root/delivery-servers-info.txt"

# Script SQL IGNORÉ — conservé pour compatibilité éventuelle
cat > /root/setup-delivery-servers.sql.DISABLED <<EOF
-- ═══════════════════════════════════════════════════════════
-- DELIVERY SERVERS MAILWIZZ - PowerMTA (${PMTA_HOST}:${PMTA_PORT})
-- CRITIQUE : adresses FROM = pattern-list PowerMTA
-- ═══════════════════════════════════════════════════════════

USE ${DB_NAME};

-- ─────────────────────────────────────────────────────────
-- Delivery Server 1 : IP1 → ${SENDER1}
-- ─────────────────────────────────────────────────────────
INSERT INTO mw_delivery_server (
    customer_id, type, name, hostname, port,
    username, password, from_email, from_name,
    status, use_for, signing_enabled,
    max_connection_messages, hourly_quota, pause_after_send
) VALUES (
    1, 'smtp', 'PowerMTA IP1 - ${SENDER1}',
    '${PMTA_HOST}', ${PMTA_PORT},
    '', '',
    '${SENDER1}', 'SOS Holidays',
    'active', 'campaigns', 'yes',
    100, 1000, 0
);

-- ─────────────────────────────────────────────────────────
-- Delivery Server 2 : IP2 → ${SENDER2}
-- ─────────────────────────────────────────────────────────
INSERT INTO mw_delivery_server (
    customer_id, type, name, hostname, port,
    username, password, from_email, from_name,
    status, use_for, signing_enabled,
    max_connection_messages, hourly_quota, pause_after_send
) VALUES (
    1, 'smtp', 'PowerMTA IP2 - ${SENDER2}',
    '${PMTA_HOST}', ${PMTA_PORT},
    '', '',
    '${SENDER2}', 'SOS Holidays',
    'active', 'campaigns', 'yes',
    100, 1000, 0
);

-- ─────────────────────────────────────────────────────────
-- Delivery Server 3 : IP3 → ${SENDER3}
-- ─────────────────────────────────────────────────────────
INSERT INTO mw_delivery_server (
    customer_id, type, name, hostname, port,
    username, password, from_email, from_name,
    status, use_for, signing_enabled,
    max_connection_messages, hourly_quota, pause_after_send
) VALUES (
    1, 'smtp', 'PowerMTA IP3 - ${SENDER3}',
    '${PMTA_HOST}', ${PMTA_PORT},
    '', '',
    '${SENDER3}', 'SOS Holidays',
    'active', 'campaigns', 'yes',
    100, 1000, 0
);

-- ─────────────────────────────────────────────────────────
-- Delivery Server 4 : IP4 → ${SENDER4}
-- ─────────────────────────────────────────────────────────
INSERT INTO mw_delivery_server (
    customer_id, type, name, hostname, port,
    username, password, from_email, from_name,
    status, use_for, signing_enabled,
    max_connection_messages, hourly_quota, pause_after_send
) VALUES (
    1, 'smtp', 'PowerMTA IP4 - ${SENDER4}',
    '${PMTA_HOST}', ${PMTA_PORT},
    '', '',
    '${SENDER4}', 'SOS Holidays',
    'active', 'campaigns', 'yes',
    100, 1000, 0
);

-- ─────────────────────────────────────────────────────────
-- Delivery Server 5 : IP5 → ${SENDER5}
-- ─────────────────────────────────────────────────────────
INSERT INTO mw_delivery_server (
    customer_id, type, name, hostname, port,
    username, password, from_email, from_name,
    status, use_for, signing_enabled,
    max_connection_messages, hourly_quota, pause_after_send
) VALUES (
    1, 'smtp', 'PowerMTA IP5 - ${SENDER5}',
    '${PMTA_HOST}', ${PMTA_PORT},
    '', '',
    '${SENDER5}', 'SOS Holidays',
    'active', 'campaigns', 'yes',
    100, 1000, 0
);

-- Vérification
SELECT id, name, from_email, hostname, port, status
FROM mw_delivery_server
ORDER BY id;
EOF

chmod 600 /root/setup-delivery-servers.sql
echo "✓ Script SQL généré : /root/setup-delivery-servers.sql"
echo "  (à exécuter APRÈS le wizard MailWizz)"

# ═══════════════════════════════════════════════════════════
# FIN INSTALLATION
# ═══════════════════════════════════════════════════════════
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  INSTALLATION TERMINÉE !"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "✓ MailWizz installé sur : https://${DOMAIN}"
echo "✓ Base de données : ${DB_NAME}"
echo "✓ Mot de passe MySQL : voir /root/mysql_credentials.txt"
echo ""
echo "PROCHAINES ÉTAPES :"
echo ""
echo "1. Wizard MailWizz"
echo "   https://${DOMAIN}/install"
echo "   - Host : localhost"
echo "   - Database : ${DB_NAME}"
echo "   - Username : ${DB_USER}"
echo "   - Password : voir /root/mysql_credentials.txt"
echo ""
echo "2. Créer compte admin MailWizz"
echo ""
echo "3. Configurer les Delivery Servers"
echo "   Via Email-Engine API (automatique) :"
echo "   ─────────────────────────────────────────────────────"
echo "   POST http://VPS1:8000/api/v1/ips"
echo "   {"
echo "     \"address\": \"178.x.x.1\","
echo "     \"hostname\": \"mail.ton-domaine.com\","
echo "     \"sender_email\": \"contact@mail.ton-domaine.com\","
echo "     \"from_name\": \"Ton Nom\""
echo "   }"
echo ""
echo "   L'API crée automatiquement :"
echo "     1. virtual-mta PowerMTA (VPS2)"
echo "     2. Delivery server MailWizz (FROM = sender_email)"
echo "     3. Cohérence garantie"
echo ""
echo "   Note : Le nom email (contact@...) est libre — pas une vraie boîte"
echo ""
echo "4. Vérifier les delivery servers créés"
echo "   MailWizz Backend > Delivery Servers"
echo ""
echo "5. Vérifier logs PowerMTA (VPS2)"
echo "   tail -f /var/log/pmta/acct.csv"
echo ""
echo "═══════════════════════════════════════════════════════════"
