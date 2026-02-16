#!/bin/bash
# ============================================================================
# email-engine - Installation VPS Hetzner
# VPS: 46.225.171.192 (Nuremberg, Germany)
# Domaine: sos-holidays.com
# ============================================================================

set -e

echo "============================================"
echo "email-engine Installation sur VPS"
echo "============================================"

# Vérification root
if [ "$EUID" -ne 0 ]; then
  echo "❌ Ce script doit être exécuté en tant que root"
  exit 1
fi

# Mise à jour système
echo "📦 Mise à jour du système..."
apt update && apt upgrade -y

# Installation outils de base
echo "🔧 Installation des outils de base..."
apt install -y curl wget git vim htop net-tools ufw nginx certbot python3-certbot-nginx

# Configuration Firewall
echo "🔥 Configuration du firewall..."
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw allow 8000/tcp  # email-engine API
ufw allow 5555/tcp  # Celery Flower
ufw --force enable

# Installation Docker
echo "🐳 Installation de Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
fi

# Installation Docker Compose
echo "🐳 Installation de Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    apt install -y docker-compose
fi

# Démarrage Docker
systemctl start docker
systemctl enable docker

# Clone repository email-engine
echo "📥 Clone du repository email-engine..."
cd /opt

# Si le répertoire existe déjà, le supprimer
if [ -d "email-engine" ]; then
    echo "⚠️  Répertoire email-engine existant trouvé, sauvegarde..."
    mv email-engine email-engine.backup.$(date +%Y%m%d_%H%M%S)
fi

# Clone (utiliser le bon URL selon public/privé)
echo "Clonage depuis GitHub..."
git clone https://github.com/will383842/cold_email-engine.git email-engine

# Si le clone échoue (repo privé), afficher instructions
if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Le clone a échoué. Si le repo est privé:"
    echo "1. Créer un token sur: https://github.com/settings/tokens"
    echo "2. Cocher 'repo' permissions"
    echo "3. Relancer avec:"
    echo "   git clone https://TON_TOKEN@github.com/will383842/cold_email-engine.git email-engine"
    exit 1
fi

cd email-engine

# Configuration .env
echo "⚙️  Configuration de l'environnement..."
if [ ! -f .env ]; then
    cp .env.example .env

    # Générer passwords sécurisés
    POSTGRES_PASSWORD=$(openssl rand -base64 32)

    # Configurer .env
    sed -i "s|POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=${POSTGRES_PASSWORD}|g" .env
    sed -i "s|MAILWIZZ_API_URL=.*|MAILWIZZ_API_URL=https://sos-holidays.com/api|g" .env

    echo "✅ Fichier .env créé avec passwords sécurisés"
    echo "⚠️  IMPORTANT: Sauvegarder le password PostgreSQL: ${POSTGRES_PASSWORD}"
fi

# Démarrage des services
echo "🚀 Démarrage de email-engine..."
docker-compose up -d --build

# Attendre que les services soient prêts
echo "⏳ Attente du démarrage des services (30s)..."
sleep 30

# Vérifier status
echo "📊 Vérification du status..."
docker-compose ps

# Initialiser la base de données
echo "💾 Initialisation de la base de données..."
docker-compose exec -T api alembic upgrade head

# Peupler données de test
echo "📝 Chargement des données de test..."
docker-compose exec -T api python scripts/seed_enterprise_data.py || true

# Health check
echo "🏥 Health check..."
sleep 5
curl -f http://localhost:8000/health || echo "⚠️  API pas encore prête, attendre quelques secondes"

echo ""
echo "============================================"
echo "✅ Installation de email-engine terminée!"
echo "============================================"
echo ""
echo "Services disponibles:"
echo "- API: http://46.225.171.192:8000"
echo "- Docs: http://46.225.171.192:8000/docs"
echo "- Flower: http://46.225.171.192:5555"
echo ""
echo "Vérifier les logs:"
echo "  cd /opt/email-engine"
echo "  docker-compose logs -f api"
echo ""
echo "Prochaine étape: Installer MailWizz"
echo "============================================"
