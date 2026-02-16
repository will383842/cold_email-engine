#!/bin/bash
# ============================================================================
# MailWizz - Installation sur VPS Hetzner
# VPS: 46.225.171.192 (Nuremberg, Germany)
# Domaine: sos-holidays.com
# ============================================================================

set -e

echo "============================================"
echo "MailWizz Installation sur VPS"
echo "============================================"

# Vérification root
if [ "$EUID" -ne 0 ]; then
  echo "❌ Ce script doit être exécuté en tant que root"
  exit 1
fi

# Créer répertoire MailWizz
echo "📁 Création du répertoire MailWizz..."
cd /opt
mkdir -p mailwizz
cd mailwizz

# Créer docker-compose.yml
echo "📝 Création de docker-compose.yml..."
cat > docker-compose.yml << 'EOFCOMPOSE'
version: '3.8'

services:
  mailwizz-db:
    image: mariadb:10.11
    container_name: mailwizz-mysql
    environment:
      MYSQL_ROOT_PASSWORD: RootMailwizzPassword2026!
      MYSQL_DATABASE: mailwizz
      MYSQL_USER: mailwizz
      MYSQL_PASSWORD: MailwizzPassword2026!
    volumes:
      - mailwizz_db:/var/lib/mysql
    restart: unless-stopped
    networks:
      - mailwizz_network
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5

  mailwizz-app:
    image: twisted1919/mailwizz:latest
    container_name: mailwizz-web
    ports:
      - "8080:80"
    environment:
      DB_HOST: mailwizz-db
      DB_NAME: mailwizz
      DB_USER: mailwizz
      DB_PASS: MailwizzPassword2026!
    volumes:
      - mailwizz_data:/var/www/html
    depends_on:
      mailwizz-db:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - mailwizz_network

networks:
  mailwizz_network:
    driver: bridge

volumes:
  mailwizz_db:
  mailwizz_data:
EOFCOMPOSE

# Démarrer MailWizz
echo "🚀 Démarrage de MailWizz..."
docker-compose up -d

# Attendre démarrage
echo "⏳ Attente du démarrage (45s)..."
sleep 45

# Vérifier status
echo "📊 Vérification du status..."
docker-compose ps

# Configuration Nginx pour sos-holidays.com
echo "🌐 Configuration Nginx pour sos-holidays.com..."

# Créer configuration Nginx (sans SSL d'abord)
cat > /etc/nginx/sites-available/mailwizz << 'EOFNGINX'
server {
    listen 80;
    server_name sos-holidays.com www.sos-holidays.com;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }

    # MailWizz specific
    client_max_body_size 100M;
    proxy_connect_timeout 600;
    proxy_send_timeout 600;
    proxy_read_timeout 600;
    send_timeout 600;
}
EOFNGINX

# Activer le site
ln -sf /etc/nginx/sites-available/mailwizz /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Tester configuration Nginx
echo "🧪 Test de la configuration Nginx..."
nginx -t

if [ $? -eq 0 ]; then
    # Redémarrer Nginx
    echo "♻️  Redémarrage de Nginx..."
    systemctl restart nginx
    systemctl enable nginx
else
    echo "❌ Erreur dans la configuration Nginx"
    exit 1
fi

echo ""
echo "============================================"
echo "✅ Installation de MailWizz terminée!"
echo "============================================"
echo ""
echo "📝 IMPORTANT: Configurer DNS avant d'accéder à MailWizz"
echo ""
echo "DNS à configurer (chez ton registrar):"
echo "  Type: A"
echo "  Name: @ (ou sos-holidays.com)"
echo "  Value: 46.225.171.192"
echo "  TTL: 300"
echo ""
echo "  Type: A"
echo "  Name: www"
echo "  Value: 46.225.171.192"
echo "  TTL: 300"
echo ""
echo "Après configuration DNS (attendre 5-10 min), accéder à:"
echo "  http://sos-holidays.com"
echo ""
echo "Pour obtenir le certificat SSL ensuite, lancer:"
echo "  bash /opt/email-engine/INSTALL_SSL.sh"
echo ""
echo "============================================"
