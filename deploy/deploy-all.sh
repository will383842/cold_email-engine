#!/bin/bash
################################################################################
# DÉPLOIEMENT COMPLET EMAIL-ENGINE V2
# Architecture : 2 VPS
#   VPS1 : MailWizz + Email-Engine API (même machine)
#   VPS2 : PowerMTA dédié (envoi + IPs)
################################################################################

set -e

echo "═══════════════════════════════════════════════════════════"
echo "  DÉPLOIEMENT EMAIL-ENGINE V2"
echo "  VPS1 : MailWizz + Email-Engine API"
echo "  VPS2 : PowerMTA (5-100 IPs)"
echo "═══════════════════════════════════════════════════════════"
echo ""

# ═══════════════════════════════════════════════════════════
# CONFIGURATION (À MODIFIER)
# ═══════════════════════════════════════════════════════════
VPS1_IP="YOUR_VPS1_IP"  # MailWizz + Email-Engine API
VPS2_IP="YOUR_VPS2_IP"  # PowerMTA seul

SSH_USER="root"
SSH_KEY="~/.ssh/id_rsa"

# Chemins
DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$DEPLOY_DIR")"
MAILWIZZ_SOURCE="${PROJECT_ROOT}/mailwizz-email-engine"

# ═══════════════════════════════════════════════════════════
# ÉTAPE 0 : VALIDATION COHÉRENCE (BLOQUANT)
# Doit passer avant TOUT déploiement
# ═══════════════════════════════════════════════════════════
echo "✓ Étape 0/10 : Validation cohérence MailWizz ↔ PowerMTA..."
echo ""

"$DEPLOY_DIR/validate-coherence.sh"

# Si validate-coherence.sh retourne une erreur → exit automatique (set -e)

echo ""

# ═══════════════════════════════════════════════════════════
# VÉRIFICATIONS PRÉALABLES
# ═══════════════════════════════════════════════════════════
echo "✓ Étape 1/10 : Vérifications préalables..."
echo ""

# Vérifier mailwizz-email-engine
if [ ! -d "$MAILWIZZ_SOURCE" ]; then
    echo "❌ ERREUR : $MAILWIZZ_SOURCE manquant"
    echo "   Copie backup-cold déjà faite normalement"
    exit 1
fi

# Vérifier licence PowerMTA
if [ ! -f "$MAILWIZZ_SOURCE/pmta-license-20260216" ]; then
    echo "❌ ERREUR : Licence PowerMTA manquante dans mailwizz-email-engine/"
    exit 1
fi

# Vérifier archive MailWizz
if [ ! -f "$MAILWIZZ_SOURCE/mailwizz-prod-20260216.tar.gz" ]; then
    echo "❌ ERREUR : Archive MailWizz manquante dans mailwizz-email-engine/"
    exit 1
fi

# Vérifier PowerMTA RPM
if [ ! -f "$PROJECT_ROOT"/powermta-*.rpm ]; then
    echo "❌ ERREUR : PowerMTA RPM manquant"
    echo "   Télécharger depuis Port25 et placer dans : $PROJECT_ROOT/"
    exit 1
fi

# Vérifier .env.production
if [ ! -f "$PROJECT_ROOT/.env.production" ]; then
    echo "❌ ERREUR : .env.production manquant"
    echo "   Copier : cp .env.production.example .env.production"
    echo "   Puis remplir les valeurs"
    exit 1
fi

echo "✓ Tous les fichiers nécessaires sont présents"
echo ""

# ═══════════════════════════════════════════════════════════
# CONFIRMATION UTILISATEUR
# ═══════════════════════════════════════════════════════════
echo "═══════════════════════════════════════════════════════════"
echo "  CONFIGURATION DÉPLOIEMENT"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "VPS1 (MailWizz + Email-Engine API) : $VPS1_IP"
echo "VPS2 (PowerMTA dédié)             : $VPS2_IP"
echo ""
echo "Cette opération va :"
echo "  1. Installer MailWizz sur VPS1"
echo "  2. Installer Email-Engine API sur VPS1 (même machine)"
echo "  3. Installer PowerMTA avec IPs dédiées sur VPS2"
echo "  4. Configurer DNS (affichera instructions)"
echo ""
read -p "Confirmer déploiement ? (yes/no) : " confirm

if [ "$confirm" != "yes" ]; then
    echo "Déploiement annulé"
    exit 0
fi

echo ""

# ═══════════════════════════════════════════════════════════
# ÉTAPE 2 : PRÉPARATION FICHIERS
# ═══════════════════════════════════════════════════════════
echo "✓ Étape 2/10 : Préparation des fichiers..."
echo ""

# Copier licence PowerMTA
cp "$MAILWIZZ_SOURCE/pmta-license-20260216" "$DEPLOY_DIR/pmta-license"

# Copier config PowerMTA (backup-cold)
cp "$MAILWIZZ_SOURCE/pmta-config-20260216" "$DEPLOY_DIR/pmta-config"

# Copier archive MailWizz
cp "$MAILWIZZ_SOURCE/mailwizz-prod-20260216.tar.gz" "$DEPLOY_DIR/mailwizz.tar.gz"

# Générer clé SSH pour PowerMTA (si n'existe pas)
if [ ! -f "$PROJECT_ROOT/secrets/pmta_ssh_key" ]; then
    mkdir -p "$PROJECT_ROOT/secrets"
    ssh-keygen -t ed25519 -f "$PROJECT_ROOT/secrets/pmta_ssh_key" -N "" -C "email-engine-pmta"
    echo "✓ Clé SSH générée : secrets/pmta_ssh_key"
fi

echo "✓ Fichiers préparés"
echo ""

# ═══════════════════════════════════════════════════════════
# ÉTAPE 3 : UPLOAD FICHIERS VPS1 (MailWizz)
# ═══════════════════════════════════════════════════════════
echo "✓ Étape 3/10 : Upload fichiers vers VPS1 (MailWizz)..."
echo ""

scp -i "$SSH_KEY" "$DEPLOY_DIR/vps1-mailwizz/install.sh" "$SSH_USER@$VPS1_IP:/tmp/"
scp -i "$SSH_KEY" "$DEPLOY_DIR/mailwizz.tar.gz" "$SSH_USER@$VPS1_IP:/tmp/mailwizz-prod-20260216.tar.gz"

# IMPORTANT : On n'upload PAS le SQL (templates/segments restent dans backup-cold)

echo "✓ Fichiers uploadés sur VPS1 (app MailWizz, PAS le SQL)"
echo ""

# ═══════════════════════════════════════════════════════════
# ÉTAPE 4 : UPLOAD FICHIERS VPS2 (PowerMTA)
# ═══════════════════════════════════════════════════════════
echo "✓ Étape 4/10 : Upload fichiers vers VPS2 (PowerMTA)..."
echo ""

scp -i "$SSH_KEY" "$DEPLOY_DIR/vps2-pmta/install.sh" "$SSH_USER@$VPS2_IP:/tmp/"
scp -i "$SSH_KEY" "$DEPLOY_DIR/pmta-license" "$SSH_USER@$VPS2_IP:/tmp/pmta-license"
scp -i "$SSH_KEY" "$DEPLOY_DIR/pmta-config" "$SSH_USER@$VPS2_IP:/tmp/pmta-config-20260216"
scp -i "$SSH_KEY" "$PROJECT_ROOT"/powermta-*.rpm "$SSH_USER@$VPS2_IP:/tmp/" 2>/dev/null || echo "⚠️  PowerMTA RPM à uploader manuellement"

echo "✓ Fichiers uploadés sur VPS2 (licence + config backup-cold)"
echo ""

# ═══════════════════════════════════════════════════════════
# ÉTAPE 5 : INSTALLATION VPS1 (MailWizz)
# ═══════════════════════════════════════════════════════════
echo "✓ Étape 5/10 : Installation MailWizz sur VPS1..."
echo ""

ssh -i "$SSH_KEY" "$SSH_USER@$VPS1_IP" << 'ENDSSH'
cd /tmp
chmod +x install.sh
./install.sh 2>&1 | tee mailwizz_install.log
ENDSSH

echo "✓ MailWizz installé sur VPS1"
echo ""

# ═══════════════════════════════════════════════════════════
# ÉTAPE 6 : INSTALLATION VPS2 (PowerMTA)
# ═══════════════════════════════════════════════════════════
echo "✓ Étape 6/10 : Installation PowerMTA sur VPS2..."
echo ""

ssh -i "$SSH_KEY" "$SSH_USER@$VPS2_IP" << 'ENDSSH'
cd /tmp
chmod +x install.sh
./install.sh 2>&1 | tee pmta_install.log
ENDSSH

echo "✓ PowerMTA installé sur VPS2"
echo ""

# ═══════════════════════════════════════════════════════════
# ÉTAPE 7 : RÉCUPÉRATION CLÉS DKIM
# ═══════════════════════════════════════════════════════════
echo "✓ Étape 7/10 : Récupération clés DKIM publiques..."
echo ""

mkdir -p "$PROJECT_ROOT/dkim-keys"

for i in {1..5}; do
    scp -i "$SSH_KEY" "$SSH_USER@$VPS2_IP:/etc/pmta/dkim/mail${i}.pub.txt" \
        "$PROJECT_ROOT/dkim-keys/mail${i}.pub.txt"
done

echo "✓ Clés DKIM récupérées : dkim-keys/"
echo ""

# ═══════════════════════════════════════════════════════════
# ÉTAPE 8 : EMAIL-ENGINE API SUR VPS1 (même machine que MailWizz)
# ═══════════════════════════════════════════════════════════
echo "✓ Étape 8/10 : Déploiement Email-Engine API sur VPS1..."
echo "  (même machine que MailWizz → communication localhost)"
echo ""

# Installer Docker sur VPS1 si pas déjà fait
ssh -i "$SSH_KEY" "$SSH_USER@$VPS1_IP" << 'ENDSSH'
if ! command -v docker &> /dev/null; then
    echo "Installation Docker..."
    curl -fsSL https://get.docker.com | bash
    systemctl enable docker
    systemctl start docker
fi
if ! command -v docker-compose &> /dev/null; then
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
        -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
fi
ENDSSH

# Upload Email-Engine (sans mailwizz-email-engine qui est lourd)
rsync -avz \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='mailwizz-email-engine' \
    --exclude='backup-source' \
    --exclude='logs' \
    -e "ssh -i $SSH_KEY" \
    "$PROJECT_ROOT/" "$SSH_USER@$VPS1_IP:/opt/email-engine/"

# Démarrer containers Email-Engine
ssh -i "$SSH_KEY" "$SSH_USER@$VPS1_IP" << 'ENDSSH'
cd /opt/email-engine

# MailWizz en localhost = pas besoin d'URL externe
export MAILWIZZ_URL="http://localhost/api"

docker-compose -f docker-compose.prod.yml --env-file .env.production up -d --build
ENDSSH

echo "✓ Email-Engine API déployé sur VPS1 (avec MailWizz)"
echo ""

# ═══════════════════════════════════════════════════════════
# ÉTAPE 9 : INITIALISATION BASE DE DONNÉES
# ═══════════════════════════════════════════════════════════
echo "✓ Étape 9/10 : Initialisation base de données..."
echo ""

ssh -i "$SSH_KEY" "$SSH_USER@$VPS1_IP" << 'ENDSSH'
cd /opt/email-engine
docker-compose -f docker-compose.prod.yml exec api alembic upgrade head
docker-compose -f docker-compose.prod.yml exec api python scripts/init_db.py
ENDSSH

echo "✓ Base de données initialisée"
echo ""

# ═══════════════════════════════════════════════════════════
# ÉTAPE 10 : GÉNÉRATION CONFIGURATION DNS
# ═══════════════════════════════════════════════════════════
echo "✓ Étape 10/10 : Génération configuration DNS..."
echo ""

cd "$DEPLOY_DIR"
./dns-helper.sh > dns-config.txt

echo "✓ Configuration DNS générée : deploy/dns-config.txt"
echo ""

# ═══════════════════════════════════════════════════════════
# DÉPLOIEMENT TERMINÉ
# ═══════════════════════════════════════════════════════════
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  ✅ DÉPLOIEMENT TERMINÉ !"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "SERVICES DÉPLOYÉS :"
echo "  ✓ VPS1 (MailWizz + Email-Engine) : https://sos-holidays.com"
echo "           Email-Engine API         : http://VPS1_IP:8000"
echo "           Communication interne    : localhost (ultra rapide)"
echo "  ✓ VPS2 (PowerMTA)                : SMTP relay sur port 2525"
echo ""
echo "PROCHAINES ÉTAPES :"
echo ""
echo "1. CONFIGURATION MAILWIZZ (VPS1)"
echo "   - Ouvrir : https://sos-holidays.com/install"
echo "   - Suivre wizard d'installation"
echo "   - Credentials MySQL : voir /root/mysql_credentials.txt sur VPS1"
echo "   - Créer compte admin"
echo "   - Générer API key : Settings > API > Create key"
echo "   - Ajouter API key dans .env.production (MAILWIZZ_API_KEY)"
echo ""
echo "2. CONFIGURATION DNS (CRITIQUE)"
echo "   - Ouvrir : deploy/dns-config.txt"
echo "   - Ajouter TOUS les records dans votre DNS provider"
echo "   - Vérifier propagation (24-48h) : dig TXT mail1.sos-holidays.com"
echo ""
echo "3. CONFIGURATION PTR (REVERSE DNS)"
echo "   - Contacter votre hébergeur VPS"
echo "   - Demander configuration PTR pour les 5 IPs"
echo "   - Format : IP → mail1-5.sos-holidays.com"
echo ""
echo "4. TESTS INITIAUX"
echo "   - Test SMTP : telnet $VPS2_IP 2525"
echo "   - Test API : curl http://$VPS1_IP:8000/health"
echo "   - Test MailWizz→API : interne (localhost sur VPS1)"
echo "   - Test email : mail-tester.com (score 10/10)"
echo ""
echo "5. COPIER CLÉ SSH PUBLIQUE SUR VPS2 (pour API)"
echo "   ssh-copy-id -i secrets/pmta_ssh_key.pub root@$VPS2_IP"
echo ""
echo "6. MONITORING (sur VPS1 - même machine)"
echo "   - Prometheus : http://$VPS1_IP:9090"
echo "   - Grafana : http://$VPS1_IP:3000 (admin/VOTRE_PASSWORD)"
echo ""
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "LOGS :"
echo "  - MailWizz install : ssh $SSH_USER@$VPS1_IP 'cat /tmp/mailwizz_install.log'"
echo "  - PowerMTA install : ssh $SSH_USER@$VPS2_IP 'cat /tmp/pmta_install.log'"
echo "  - Email-Engine : docker-compose logs -f api"
echo ""
echo "DOCUMENTATION :"
echo "  - Architecture : README.md"
echo "  - Phase 1 : PHASE-1-VERIFICATION-FINALE.md"
echo "  - Phase 2 : PHASE-2-IMPLEMENTATION.md"
echo ""
echo "═══════════════════════════════════════════════════════════"
