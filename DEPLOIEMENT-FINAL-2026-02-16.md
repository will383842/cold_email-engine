# 🚀 DÉPLOIEMENT FINAL - EMAIL-ENGINE V2

**Date** : 16 février 2026 21:00
**Phase** : Phase 2 - Déploiement Production
**Statut** : ✅ Scripts prêts pour déploiement

---

## 📋 TABLE DES MATIÈRES

1. [Vue d'ensemble](#vue-densemble)
2. [Prérequis](#prérequis)
3. [Architecture déployée](#architecture-déployée)
4. [Installation rapide](#installation-rapide)
5. [Installation détaillée](#installation-détaillée)
6. [Configuration DNS](#configuration-dns)
7. [Tests post-déploiement](#tests-post-déploiement)
8. [Monitoring](#monitoring)
9. [Troubleshooting](#troubleshooting)

---

## 🎯 VUE D'ENSEMBLE

### Architecture finale

```
┌─────────────────────────────────────────────────────────────┐
│                    EMAIL-ENGINE V2                          │
│          (Système NEUF, distinct de backup-cold)            │
└─────────────────────────────────────────────────────────────┘

┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│   VPS 1      │      │   VPS 2      │      │   VPS 3      │
│  MailWizz    │◄────►│  PowerMTA    │◄────►│ Email-Engine │
│              │      │              │      │     API      │
│ sos-holidays │      │   5 IPs      │      │ (ou local)   │
│    .com      │      │ 5 domaines   │      │              │
└──────────────┘      └──────────────┘      └──────────────┘
     VIDE              Isolation                FastAPI
  (0 templates)        complète              PostgreSQL
  (0 campagnes)     (1 email/IP)               Redis
```

### Principe d'isolation (CRITIQUE)

```
IP1 → mail1.sos-holidays.com → contact@mail1.sos-holidays.com
IP2 → mail2.sos-holidays.com → support@mail2.sos-holidays.com
IP3 → mail3.sos-holidays.com → hello@mail3.sos-holidays.com
IP4 → mail4.sos-holidays.com → info@mail4.sos-holidays.com
IP5 → mail5.sos-holidays.com → noreply@mail5.sos-holidays.com
```

**Pourquoi ?**
- 1 email par IP = isolation complète
- Blacklist d'1 IP n'affecte pas les autres
- Aucun pattern visible pour détection bot
- Réputation indépendante par IP

---

## ✅ PRÉREQUIS

### Matériel

- **VPS 1** : 2 CPU, 4 GB RAM, 50 GB SSD (MailWizz)
- **VPS 2** : 4 CPU, 8 GB RAM, 100 GB SSD (PowerMTA)
- **VPS 3** : 4 CPU, 8 GB RAM, 100 GB SSD (Email-Engine API)
- **5 IPs dédiées** sur VPS2

### Logiciels

- Ubuntu 22.04 LTS (recommandé) ou CentOS 8
- Docker 24+ et Docker Compose v2
- SSH access root sur les 3 VPS
- Git

### Fichiers nécessaires

```bash
email-engine/
├── backup-source/
│   └── pmta-license-20260216        # ✅ Licence PowerMTA (391 bytes)
├── powermta-5.0r*.rpm               # ✅ RPM PowerMTA (télécharger)
├── .env.production                  # ✅ À créer depuis .example
└── secrets/
    └── pmta_ssh_key                 # ✅ Généré auto si absent
```

### Domaine et DNS

- Domaine principal : `sos-holidays.com`
- Accès panel DNS (Cloudflare, OVH, etc.)
- Certificats SSL : Let's Encrypt (auto via Certbot)

---

## 🏗️ ARCHITECTURE DÉPLOYÉE

### VPS 1 : MailWizz (sos-holidays.com)

**Stack** :
- Apache 2.4
- PHP 8.1
- MySQL 8.0
- MailWizz latest (VIDE au départ)

**Ports** :
- 80/443 (HTTP/HTTPS)
- 22 (SSH)

**Rôle** :
- Interface web gestion campagnes
- API REST pour Email-Engine
- Tracking opens/clicks
- Bounce handling

---

### VPS 2 : PowerMTA (mail.sos-holidays.com)

**Stack** :
- PowerMTA 5.0r1
- 5 Virtual MTAs (isolation)
- 5 clés DKIM

**Ports** :
- 2525 (SMTP relay depuis MailWizz)
- 22 (SSH pour gestion config)
- 1983 (HTTP management localhost)

**Rôle** :
- Envoi SMTP haute performance
- Gestion queues
- Retry logic
- Logs détaillés

**Configuration** :
```ini
# Pattern-list : 1 email = 1 VMTA
<pattern-list sender-to-vmta>
    contact@mail1.sos-holidays.com   vmta-mail1
    support@mail2.sos-holidays.com   vmta-mail2
    hello@mail3.sos-holidays.com     vmta-mail3
    info@mail4.sos-holidays.com      vmta-mail4
    noreply@mail5.sos-holidays.com   vmta-mail5
</pattern-list>
```

---

### VPS 3 (ou local) : Email-Engine API

**Stack** :
- FastAPI (Python 3.11)
- PostgreSQL 15
- Redis 7
- Celery (worker + beat)
- Prometheus + Grafana

**Ports** :
- 8000 (API REST)
- 5432 (PostgreSQL localhost)
- 6379 (Redis localhost)
- 9090 (Prometheus localhost)
- 3000 (Grafana localhost)

**Rôle** :
- Orchestration générale
- Gestion warmup IPs
- Multi-tenant (client-1, backlink-engine, telegram-engine)
- Monitoring temps réel
- Webhook bounces

---

## 🚀 INSTALLATION RAPIDE

### Méthode automatisée (recommandée)

```bash
# 1. Cloner repo
git clone https://github.com/your-org/email-engine.git
cd email-engine

# 2. Copier backup-source
cp -r ../Outils\ d\'emailing/backup-cold backup-source

# 3. Télécharger PowerMTA RPM (depuis Port25)
# Placer dans : email-engine/powermta-5.0r*.rpm

# 4. Configurer environnement
cp .env.production.example .env.production
nano .env.production  # Remplir IPs, API keys, etc.

# 5. Éditer IPs dans script déploiement
nano deploy/deploy-all.sh
# Modifier : VPS1_IP, VPS2_IP, VPS3_IP

# 6. Lancer déploiement automatique
cd deploy
./deploy-all.sh
```

**Durée** : 20-30 minutes
**Résultat** : 3 VPS configurés, Email-Engine opérationnel

---

## 📖 INSTALLATION DÉTAILLÉE

### Étape 1 : Préparation locale

```bash
# Cloner projet
git clone https://github.com/your-org/email-engine.git
cd email-engine

# Copier backup-source (licence PowerMTA)
cp -r ../Outils\ d\'emailing/backup-cold backup-source

# Vérifier licence
ls -lh backup-source/pmta-license-20260216
# Doit afficher : 391 bytes

# Télécharger PowerMTA
# URL : https://www.port25.com/downloads/
# Placer : email-engine/powermta-5.0r1.rpm

# Créer .env.production
cp .env.production.example .env.production
```

**Éditer `.env.production`** :

```bash
# IPs des 5 domaines
IP1=178.xxx.xxx.1
IP2=178.xxx.xxx.2
IP3=178.xxx.xxx.3
IP4=178.xxx.xxx.4
IP5=178.xxx.xxx.5

# PostgreSQL
POSTGRES_PASSWORD=votre_mot_de_passe_fort_ici

# MailWizz (à générer après install)
MAILWIZZ_API_KEY=sera_généré_étape_3

# PowerMTA SSH
PMTA_SSH_HOST=178.xxx.xxx.xxx  # VPS2 IP
```

---

### Étape 2 : Déploiement VPS1 (MailWizz)

**Option A : Script automatique**

```bash
cd deploy
nano vps1-mailwizz/install.sh  # Vérifier DOMAIN variable

# Upload et exécution
scp vps1-mailwizz/install.sh root@VPS1_IP:/tmp/
ssh root@VPS1_IP
cd /tmp
chmod +x install.sh
./install.sh
```

**Option B : Manuel**

```bash
# Sur VPS1
ssh root@VPS1_IP

# 1. Installer LAMP
apt update && apt upgrade -y
apt install -y apache2 mysql-server php8.1 php8.1-cli php8.1-mysql \
    php8.1-mbstring php8.1-xml php8.1-curl php8.1-zip php8.1-gd \
    php8.1-intl php8.1-imap php8.1-bcmath unzip curl

# 2. Créer base MySQL
mysql -u root -p
```

```sql
CREATE DATABASE mailwizz_v2 CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'mailwizz'@'localhost' IDENTIFIED BY 'STRONG_PASSWORD';
GRANT ALL PRIVILEGES ON mailwizz_v2.* TO 'mailwizz'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

```bash
# 3. Télécharger MailWizz
cd /var/www/html
rm -rf * 2>/dev/null || true

# Option A : wget (si URL publique disponible)
wget https://www.mailwizz.com/downloads/mailwizz-latest.zip
unzip mailwizz-latest.zip

# Option B : Upload manuel
# scp mailwizz-latest.zip root@VPS1:/var/www/html/
# unzip mailwizz-latest.zip

# Permissions
chown -R www-data:www-data /var/www/html
chmod -R 755 /var/www/html
chmod -R 777 /var/www/html/apps/*/runtime
chmod -R 777 /var/www/html/apps/*/assets

# 4. Configurer Apache
cat > /etc/apache2/sites-available/sos-holidays.com.conf <<EOF
<VirtualHost *:80>
    ServerName sos-holidays.com
    ServerAdmin admin@sos-holidays.com
    DocumentRoot /var/www/html

    <Directory /var/www/html>
        Options -Indexes +FollowSymLinks
        AllowOverride All
        Require all granted
    </Directory>

    ErrorLog \${APACHE_LOG_DIR}/sos-holidays.com_error.log
    CustomLog \${APACHE_LOG_DIR}/sos-holidays.com_access.log combined
</VirtualHost>
EOF

a2ensite sos-holidays.com.conf
a2enmod rewrite
a2dissite 000-default.conf
systemctl restart apache2

# 5. SSL (Let's Encrypt)
apt install -y certbot python3-certbot-apache
certbot --apache -d sos-holidays.com --non-interactive --agree-tos --email admin@sos-holidays.com

# 6. Cron MailWizz
(crontab -l 2>/dev/null; echo "* * * * * /usr/bin/php /var/www/html/apps/console/console.php send-campaigns >/dev/null 2>&1") | crontab -
(crontab -l 2>/dev/null; echo "*/5 * * * * /usr/bin/php /var/www/html/apps/console/console.php process-bounces >/dev/null 2>&1") | crontab -
```

**Finaliser installation web** :

1. Ouvrir : `https://sos-holidays.com/install`
2. Accepter licence
3. Base de données :
   - Host : `localhost`
   - Database : `mailwizz_v2`
   - User : `mailwizz`
   - Password : (celui défini ci-dessus)
4. Créer compte admin
5. Générer API key : `Settings > API > Create API key`
6. Copier API key dans `.env.production`

---

### Étape 3 : Déploiement VPS2 (PowerMTA)

**Option A : Script automatique**

```bash
cd deploy

# Upload fichiers
scp vps2-pmta/install.sh root@VPS2_IP:/tmp/
scp ../backup-source/pmta-license-20260216 root@VPS2_IP:/tmp/pmta-license
scp ../powermta-*.rpm root@VPS2_IP:/tmp/

# Exécution
ssh root@VPS2_IP
cd /tmp
chmod +x install.sh
./install.sh
```

**Option B : Manuel**

```bash
# Sur VPS2
ssh root@VPS2_IP

# 1. Installer PowerMTA
cd /tmp
rpm -ivh powermta-*.rpm  # CentOS/RHEL
# OU
dpkg -i powermta-*.deb   # Ubuntu/Debian

# 2. Copier licence
mkdir -p /etc/pmta
cp /tmp/pmta-license /etc/pmta/license
chmod 644 /etc/pmta/license

# 3. Générer clés DKIM (5 clés)
mkdir -p /etc/pmta/dkim
for i in {1..5}; do
    openssl genrsa -out /etc/pmta/dkim/mail${i}.pem 2048
    chmod 600 /etc/pmta/dkim/mail${i}.pem

    # Extraire clé publique
    openssl rsa -in /etc/pmta/dkim/mail${i}.pem -pubout -outform PEM | \
        grep -v "PUBLIC KEY" | \
        tr -d '\n' > /etc/pmta/dkim/mail${i}.pub.txt
done

# 4. Créer configuration
cat > /etc/pmta/config <<'EOF'
# [Copier contenu de vps2-pmta/install.sh lignes 87-176]
# Modifier IPs : IP1, IP2, IP3, IP4, IP5
EOF

# 5. Démarrer PowerMTA
systemctl enable pmta
systemctl start pmta
systemctl status pmta

# 6. Vérifier
pmta show status
tail -f /var/log/pmta/acct.csv
```

**Récupérer clés DKIM publiques** :

```bash
# Sur local
for i in {1..5}; do
    scp root@VPS2_IP:/etc/pmta/dkim/mail${i}.pub.txt dkim-keys/
done
```

---

### Étape 4 : Déploiement VPS3 (Email-Engine API)

**Option A : VPS distant**

```bash
# Upload projet
rsync -avz --exclude='node_modules' --exclude='.git' --exclude='__pycache__' \
    -e "ssh" \
    ./ root@VPS3_IP:/opt/email-engine/

# Déployer
ssh root@VPS3_IP
cd /opt/email-engine

# Copier .env
scp .env.production root@VPS3_IP:/opt/email-engine/.env.production

# Démarrer containers
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d --build

# Initialiser BDD
docker-compose -f docker-compose.prod.yml exec api alembic upgrade head
docker-compose -f docker-compose.prod.yml exec api python scripts/init_db.py

# Vérifier
docker-compose -f docker-compose.prod.yml ps
docker-compose -f docker-compose.prod.yml logs -f api
```

**Option B : Local**

```bash
cd email-engine
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d --build

# Initialiser BDD
docker-compose -f docker-compose.prod.yml exec api alembic upgrade head
docker-compose -f docker-compose.prod.yml exec api python scripts/init_db.py

# Vérifier
curl http://localhost:8000/health
```

---

## 🌐 CONFIGURATION DNS

### Générer configuration

```bash
cd deploy
./dns-helper.sh > dns-config.txt
```

### Ajouter records DNS

Pour **CHAQUE** domaine (mail1-5.sos-holidays.com) :

#### 1. A Record

```
Nom    : mail1.sos-holidays.com
Type   : A
Valeur : 178.xxx.xxx.1
TTL    : 3600
```

#### 2. SPF Record

```
Nom    : mail1.sos-holidays.com
Type   : TXT
Valeur : "v=spf1 ip4:178.xxx.xxx.1 -all"
TTL    : 3600
```

#### 3. DKIM Record

```
Nom    : mail._domainkey.mail1.sos-holidays.com
Type   : TXT
Valeur : "v=DKIM1; k=rsa; p=[CLÉ_PUBLIQUE]"
TTL    : 3600
```

**Extraire clé publique** :

```bash
cat dkim-keys/mail1.pub.txt
```

#### 4. DMARC Record

```
Nom    : _dmarc.mail1.sos-holidays.com
Type   : TXT
Valeur : "v=DMARC1; p=quarantine; rua=mailto:dmarc@sos-holidays.com; pct=100; adkim=s; aspf=s"
TTL    : 3600
```

#### 5. PTR Record (Reverse DNS)

**Chez votre hébergeur VPS** (Hetzner, OVH, etc.) :

```
IP  : 178.xxx.xxx.1
PTR : mail1.sos-holidays.com
```

**Répéter pour les 5 domaines (mail1-5.sos-holidays.com)**

---

## ✅ TESTS POST-DÉPLOIEMENT

### 1. Vérifier DNS (attendre 24-48h propagation)

```bash
# SPF
dig TXT mail1.sos-holidays.com +short

# DKIM
dig TXT mail._domainkey.mail1.sos-holidays.com +short

# DMARC
dig TXT _dmarc.mail1.sos-holidays.com +short

# PTR (reverse)
dig -x 178.xxx.xxx.1 +short
```

### 2. Test SMTP PowerMTA

```bash
telnet VPS2_IP 2525

EHLO test.com
MAIL FROM:<contact@mail1.sos-holidays.com>
RCPT TO:<test@gmail.com>
DATA
Subject: Test Email-Engine V2

Test email depuis PowerMTA.
.
QUIT
```

### 3. Test API Email-Engine

```bash
# Health check
curl http://VPS3_IP:8000/health

# Ajouter IP
curl -X POST http://VPS3_IP:8000/api/v1/ips \
  -H "X-API-KEY: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "ip": "178.xxx.xxx.1",
    "domain": "mail1.sos-holidays.com",
    "sender_email": "contact@mail1.sos-holidays.com",
    "sender_name": "Contact SOS Holidays",
    "status": "warming"
  }'

# Lister IPs
curl http://VPS3_IP:8000/api/v1/ips \
  -H "X-API-KEY: your_api_key"
```

### 4. Test mail-tester.com

```bash
# Envoyer email à adresse unique mail-tester
# Via API Email-Engine ou MailWizz

# Vérifier score : doit être 10/10
```

### 5. Test Port25 (authentification)

```bash
# Envoyer email à :
check-auth@verifier.port25.com

# Recevoir rapport détaillé SPF/DKIM/DMARC
```

---

## 📊 MONITORING

### Prometheus

**URL** : `http://VPS3_IP:9090`

**Métriques disponibles** :
- `email_engine_emails_sent_total`
- `email_engine_bounce_rate`
- `email_engine_ip_warmup_quota`
- `email_engine_api_latency_seconds`

### Grafana

**URL** : `http://VPS3_IP:3000`
**Login** : `admin` / (mot de passe dans `.env.production`)

**Dashboards à créer** :
1. Emails envoyés par IP
2. Bounce rate par domaine
3. Warmup progress (quotas)
4. API latency
5. Database query time

### Logs

```bash
# Email-Engine API
docker-compose -f docker-compose.prod.yml logs -f api

# Celery worker
docker-compose -f docker-compose.prod.yml logs -f celery-worker

# PowerMTA
ssh root@VPS2_IP
tail -f /var/log/pmta/acct.csv

# MailWizz
ssh root@VPS1_IP
tail -f /var/log/apache2/sos-holidays.com_error.log
```

---

## 🔧 TROUBLESHOOTING

### Problème : PowerMTA ne démarre pas

```bash
# Vérifier licence
cat /etc/pmta/license

# Tester config
pmta test config

# Vérifier logs
tail -100 /var/log/pmta/log

# Redémarrer
systemctl restart pmta
```

### Problème : MailWizz 500 error

```bash
# Vérifier permissions
chown -R www-data:www-data /var/www/html
chmod -R 777 /var/www/html/apps/*/runtime

# Vérifier logs Apache
tail -100 /var/log/apache2/sos-holidays.com_error.log

# Vérifier PHP
php -v
php -m | grep -E 'mysql|mbstring|xml|curl'
```

### Problème : Email-Engine API erreur 500

```bash
# Vérifier containers
docker-compose -f docker-compose.prod.yml ps

# Logs détaillés
docker-compose -f docker-compose.prod.yml logs --tail=100 api

# Vérifier base de données
docker-compose -f docker-compose.prod.yml exec postgres psql -U email_engine -d email_engine_v2 -c "\dt"

# Recréer containers
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d --build
```

### Problème : Emails marqués spam

```bash
# Vérifier DNS
./deploy/dns-helper.sh

# Tester SPF/DKIM/DMARC
https://mxtoolbox.com/SuperTool.aspx

# Vérifier IP reputation
https://www.senderscore.org/

# Vérifier warmup
# → Respecter quotas progressifs (50/100/200/400/800/1600)
```

---

## 📚 RÉFÉRENCES

### Documentation créée

1. **VERIFICATION-COMPLETE-2026-02-16.md** (41 KB)
   - Vérification Phase 1
   - Flow E2E complet
   - Liste 100+ fonctionnalités

2. **SEPARATION-SYSTEMES-V1-V2.md** (9.2 KB)
   - Clarification backup-cold vs Email-Engine
   - Principes séparation

3. **PHASE-2-IMPLEMENTATION.md** (en cours)
   - Architecture isolation emails
   - Configuration 5 IPs

4. **Ce fichier** (DEPLOIEMENT-FINAL-2026-02-16.md)
   - Guide déploiement complet

### Scripts créés

```
deploy/
├── vps1-mailwizz/
│   └── install.sh              # Install MailWizz VIDE
├── vps2-pmta/
│   └── install.sh              # Install PowerMTA 5 IPs
├── dns-helper.sh               # Générer config DNS
└── deploy-all.sh               # Orchestration complète
```

### Fichiers configuration

```
email-engine/
├── docker-compose.prod.yml     # Production Docker
├── .env.production.example     # Template env vars
├── monitoring/
│   └── prometheus.yml          # Config Prometheus
└── backup-source/
    └── pmta-license-20260216   # Licence perpétuelle
```

---

## ✅ CHECKLIST FINALE

### Avant déploiement

- [ ] Backup-source copié (223 MB)
- [ ] PowerMTA RPM téléchargé
- [ ] `.env.production` rempli
- [ ] 3 VPS provisionnés
- [ ] 5 IPs dédiées sur VPS2
- [ ] Accès SSH root aux 3 VPS
- [ ] Domaine configuré (DNS provider accessible)

### Pendant déploiement

- [ ] VPS1 : MailWizz installé
- [ ] VPS1 : SSL configuré (Let's Encrypt)
- [ ] VPS1 : MailWizz wizard complété
- [ ] VPS1 : API key générée
- [ ] VPS2 : PowerMTA installé
- [ ] VPS2 : 5 clés DKIM générées
- [ ] VPS2 : PowerMTA démarré
- [ ] VPS3 : Email-Engine déployé
- [ ] VPS3 : Base de données initialisée

### Post-déploiement

- [ ] DNS : 5 A records ajoutés
- [ ] DNS : 5 SPF records ajoutés
- [ ] DNS : 5 DKIM records ajoutés
- [ ] DNS : 5 DMARC records ajoutés
- [ ] DNS : 5 PTR records (chez hébergeur)
- [ ] DNS : Propagation vérifiée (24-48h)
- [ ] Tests : SMTP PowerMTA OK
- [ ] Tests : API Email-Engine OK
- [ ] Tests : mail-tester.com 10/10
- [ ] Tests : Port25 auth report OK
- [ ] Monitoring : Prometheus opérationnel
- [ ] Monitoring : Grafana dashboards créés

---

**Déploiement créé le** : 16 février 2026 21:00
**Phase** : Phase 2 complète
**Statut** : ✅ Prêt pour déploiement production
**Prochaine étape** : Exécuter `./deploy/deploy-all.sh`
