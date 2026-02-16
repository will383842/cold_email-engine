#!/bin/bash
# ============================================================================
# SSL Certificate (Let's Encrypt) pour sos-holidays.com
# VPS: 46.225.171.192
# IMPORTANT: Lancer ce script APRÈS avoir configuré le DNS
# ============================================================================

set -e

echo "============================================"
echo "Installation SSL pour sos-holidays.com"
echo "============================================"

# Vérification root
if [ "$EUID" -ne 0 ]; then
  echo "❌ Ce script doit être exécuté en tant que root"
  exit 1
fi

# Vérifier que le domaine pointe bien vers ce serveur
echo "🔍 Vérification DNS..."
SERVER_IP=$(curl -s ifconfig.me)
DOMAIN_IP=$(dig +short sos-holidays.com | tail -n1)

echo "IP du serveur: $SERVER_IP"
echo "IP du domaine: $DOMAIN_IP"

if [ "$SERVER_IP" != "$DOMAIN_IP" ]; then
    echo ""
    echo "⚠️  ATTENTION: Le DNS ne pointe pas encore vers ce serveur!"
    echo "Serveur: $SERVER_IP"
    echo "Domaine: $DOMAIN_IP"
    echo ""
    echo "Configure d'abord le DNS chez ton registrar:"
    echo "  Type: A"
    echo "  Name: @"
    echo "  Value: $SERVER_IP"
    echo ""
    read -p "Continuer quand même? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Obtenir certificat SSL avec Certbot
echo "🔒 Obtention du certificat SSL Let's Encrypt..."
certbot --nginx -d sos-holidays.com -d www.sos-holidays.com --non-interactive --agree-tos --email admin@sos-holidays.com --redirect

if [ $? -eq 0 ]; then
    echo ""
    echo "============================================"
    echo "✅ SSL installé avec succès!"
    echo "============================================"
    echo ""
    echo "MailWizz accessible sur:"
    echo "  https://sos-holidays.com ✅"
    echo "  https://www.sos-holidays.com ✅"
    echo ""
    echo "Le certificat se renouvellera automatiquement."
    echo ""
    echo "Prochaine étape:"
    echo "1. Accéder à https://sos-holidays.com"
    echo "2. Compléter le wizard d'installation MailWizz"
    echo "3. Générer une API key dans Settings > API Keys"
    echo "4. Configurer email-engine avec cette API key"
    echo "============================================"
else
    echo ""
    echo "❌ Erreur lors de l'installation SSL"
    echo ""
    echo "Vérifier que:"
    echo "1. Le DNS est bien configuré (sos-holidays.com → $SERVER_IP)"
    echo "2. Nginx fonctionne (systemctl status nginx)"
    echo "3. Le port 80 est accessible de l'extérieur"
    echo ""
    echo "Réessayer après correction:"
    echo "  bash /opt/email-engine/INSTALL_SSL.sh"
fi
