#!/bin/bash
# ============================================================================
# MailWizz - Installation depuis backup de production
# VPS: 46.225.171.192 (Nuremberg, Germany)
# Domaine: sos-holidays.com
# ============================================================================

set -e

echo "============================================"
echo "MailWizz Installation depuis backup"
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
    image: php:8.1-apache
    container_name: mailwizz-web
    ports:
      - "8080:80"
    volumes:
      - mailwizz_data:/var/www/html
    depends_on:
      mailwizz-db:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - mailwizz_network
    environment:
      - DB_HOST=mailwizz-db
      - DB_NAME=mailwizz
      - DB_USER=mailwizz
      - DB_PASS=MailwizzPassword2026!

networks:
  mailwizz_network:
    driver: bridge

volumes:
  mailwizz_db:
  mailwizz_data:
EOFCOMPOSE

# Démarrer MariaDB
echo "🚀 Démarrage de MariaDB..."
docker-compose up -d mailwizz-db

# Attendre MariaDB
echo "⏳ Attente de MariaDB (30s)..."
sleep 30

# Restaurer la base de données
if [ -f "/opt/mailapp-prod-20260216.sql.gz" ]; then
    echo "💾 Restauration de la base de données..."
    gunzip -c /opt/mailapp-prod-20260216.sql.gz | docker exec -i mailwizz-mysql mysql -uroot -pRootMailwizzPassword2026! mailwizz
    echo "✅ Base de données restaurée"
else
    echo "⚠️  Fichier SQL non trouvé, skip restauration"
fi

# Démarrer le conteneur PHP/Apache
echo "🚀 Démarrage de l'application..."
docker-compose up -d mailwizz-app

# Installer extensions PHP nécessaires
echo "📦 Installation des extensions PHP..."
docker exec mailwizz-web bash -c "apt-get update && apt-get install -y \
    libzip-dev \
    libpng-dev \
    libjpeg-dev \
    libfreetype6-dev \
    libonig-dev \
    libxml2-dev \
    libcurl4-openssl-dev \
    && docker-php-ext-configure gd --with-freetype --with-jpeg \
    && docker-php-ext-install -j\$(nproc) \
        pdo \
        pdo_mysql \
        mysqli \
        mbstring \
        xml \
        curl \
        zip \
        gd \
        intl \
    && a2enmod rewrite \
    && service apache2 restart"

# Extraire les fichiers MailWizz
if [ -f "/opt/mailwizz-prod-20260216.tar.gz" ]; then
    echo "📂 Extraction des fichiers MailWizz..."
    docker exec mailwizz-web bash -c "cd /var/www/html && tar -xzf /opt/mailwizz-prod-20260216.tar.gz --strip-components=1"
    docker exec mailwizz-web chown -R www-data:www-data /var/www/html
    echo "✅ Fichiers MailWizz extraits"
else
    echo "⚠️  Archive MailWizz non trouvée"
fi

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
echo "MailWizz accessible sur:"
echo "  http://sos-holidays.com"
echo "  http://www.sos-holidays.com"
echo ""
echo "Pour obtenir le certificat SSL, lancer:"
echo "  bash /opt/email-engine/INSTALL_SSL.sh"
echo ""
echo "============================================"
