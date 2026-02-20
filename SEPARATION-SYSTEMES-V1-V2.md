# 🔒 SÉPARATION TOTALE : backup-cold (V1) vs Email-Engine (V2)

**Date** : 16 février 2026 18:45
**IMPORTANT** : Les 2 systèmes sont COMPLÈTEMENT DISTINCTS

---

## 🎯 PRINCIPE FONDAMENTAL

```
backup-cold (V1) = Système historique COMPLET
  └── Garde ses 106 templates + 77 campagnes
  └── Reste intact dans son dossier
  └── Archive/référence

Email-Engine (V2) = Système nouveau VIERGE
  └── MailWizz vide (0 templates, 0 campagnes)
  └── Tout créé depuis zéro via API
  └── Production moderne
```

**❌ ON NE MIGRE PAS les templates/campagnes de V1 vers V2**

---

## 📦 CE QU'ON UTILISE DE BACKUP-COLD

### ✅ Infrastructure seulement

```
De backup-cold/ on prend :

1. ✅ pmta-license-20260216 (391 bytes)
   → Licence perpétuelle valide
   → Même licence pour V2

2. ✅ pmta-config-20260216 (8.9 KB)
   → STRUCTURE de config seulement
   → On adapte pour nos 5 IPs
   → On change domaines
   → Mais base config identique
```

### ❌ Ce qu'on NE prend PAS

```
❌ mailwizz-prod-20260216.tar.gz (111 MB)
   → Application MailWizz : on installe version fraîche
   → Templates dedans : on ne les veut pas
   → Pas de migration

❌ mailapp-prod-20260216.sql.gz (810 KB)
   → 106 templates : V1 uniquement
   → 77 campagnes : V1 uniquement
   → Pas d'import dans V2

❌ var/www/mailwizz/
   → Extraction : pas nécessaire
   → On installe MailWizz from scratch
```

---

## 🏗️ INSTALLATION EMAIL-ENGINE V2

### VPS 1 : MailWizz (sos-holidays.com)

```bash
# 1. Installer stack LAMP
apt update && apt install -y apache2 mysql-server php8.1 php8.1-{cli,mysql,mbstring,xml,curl,zip,gd,intl}

# 2. Télécharger MailWizz LATEST (pas backup-cold)
cd /var/www/html
wget https://www.mailwizz.com/downloads/mailwizz-latest.zip
unzip mailwizz-latest.zip
chown -R www-data:www-data .

# 3. Créer base MySQL VIDE
mysql -u root -p <<EOF
CREATE DATABASE mailwizz_v2;
CREATE USER 'mailwizz'@'localhost' IDENTIFIED BY 'STRONG_PASSWORD';
GRANT ALL PRIVILEGES ON mailwizz_v2.* TO 'mailwizz'@'localhost';
FLUSH PRIVILEGES;
EOF

# 4. Installation web (wizard)
# Naviguer : https://sos-holidays.com/install
# Suivre étapes installation
# ✅ Base vide : pas de templates, pas de campagnes

# 5. SSL
certbot --apache -d sos-holidays.com
```

**Résultat** : MailWizz propre, vierge, prêt à recevoir données via API

---

### VPS 2 : PowerMTA

```bash
# 1. Installer PowerMTA
rpm -ivh pmta-5.0-*.rpm

# 2. Copier licence (de backup-cold)
cp /backup-source/pmta-license-20260216 /etc/pmta/license

# 3. Créer config NOUVELLE (pas copier backup-cold directement)
cat > /etc/pmta/config <<'EOF'
################################################################################
# POWERMTA V2 - EMAIL-ENGINE
# Date: 16 février 2026
################################################################################

postmaster admin@sos-holidays.com
host-name mail.sos-holidays.com

# SMTP Relay (depuis MailWizz)
smtp-listener 0.0.0.0:2525 {
    listen-on-tcp yes
    process-x-virtual-mta yes
}

# Virtual MTAs (5 domaines)
virtual-mta vmta-1 {
    smtp-source-host mail1.domain1.com [IP1]
    domain-key domain1.com,*,/etc/pmta/dkim/domain1.pem
}

virtual-mta vmta-2 {
    smtp-source-host mail2.domain2.com [IP2]
    domain-key domain2.com,*,/etc/pmta/dkim/domain2.pem
}

virtual-mta vmta-3 {
    smtp-source-host mail3.domain3.com [IP3]
    domain-key domain3.com,*,/etc/pmta/dkim/domain3.pem
}

virtual-mta vmta-4 {
    smtp-source-host mail4.domain4.com [IP4]
    domain-key domain4.com,*,/etc/pmta/dkim/domain4.pem
}

virtual-mta vmta-5 {
    smtp-source-host mail5.domain5.com [IP5]
    domain-key domain5.com,*,/etc/pmta/dkim/domain5.pem
}

# Logs
log-file /var/log/pmta/log
<acct-file /var/log/pmta/acct.csv>
    max-size 50M
</acct-file>

# Spool
spool /var/spool/pmta

# HTTP Management (localhost uniquement)
http-mgmt-port 1983
http-access 127.0.0.1 admin
EOF

# 4. Générer clés DKIM (5 domaines)
mkdir -p /etc/pmta/dkim
for i in {1..5}; do
  openssl genrsa -out /etc/pmta/dkim/domain${i}.pem 2048
  openssl rsa -in /etc/pmta/dkim/domain${i}.pem -pubout
done

# 5. Démarrer
systemctl start pmta
```

**Résultat** : PowerMTA prêt, 5 IPs, config propre

---

### Email-Engine API

```bash
cd /opt/email-engine

# 1. Configuration .env
cat > .env <<'EOF'
API_KEY=email_engine_v2_key

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/email_engine_v2

# Redis
REDIS_URL=redis://localhost:6379/0

# MailWizz (VPS1 - VIDE)
MAILWIZZ_URL=https://sos-holidays.com/api
MAILWIZZ_API_KEY=xxx  # Généré dans MailWizz

# PowerMTA (VPS2)
PMTA_SSH_HOST=[VPS2_IP]
PMTA_CONFIG_PATH=/etc/pmta/config

# IPs V2 (5 nouvelles IPs)
IPS_COUNT=5
EOF

# 2. Démarrer
docker-compose up -d

# 3. Initialiser BDD
alembic upgrade head

# 4. Ajouter 5 IPs
curl -X POST http://localhost:8000/api/v1/ips \
  -H "X-API-KEY: email_engine_v2_key" \
  -d '{
    "ip": "[IP1]",
    "domain": "mail1.domain1.com",
    "status": "warming"
  }'
# Répéter pour IP2, IP3, IP4, IP5
```

**Résultat** : Email-Engine opérationnel, 5 IPs en warmup

---

## 🔄 CRÉATION DE CONTENU (Templates/Campagnes)

### Via Email-Engine API (pas migration backup-cold)

```bash
# 1. Créer un template
curl -X POST http://localhost:8000/api/v2/templates \
  -H "X-API-KEY: email_engine_v2_key" \
  -d '{
    "name": "welcome_v2_fr",
    "subject": "Bienvenue sur [COMPANY]",
    "html": "<html><body>Bonjour [FNAME]...</body></html>",
    "language": "fr",
    "tenant": "client-1"
  }'

# 2. Créer une campagne
curl -X POST http://localhost:8000/api/v2/campaigns \
  -H "X-API-KEY: email_engine_v2_key" \
  -d '{
    "name": "nurture_v2_fr",
    "template_id": 1,
    "type": "autoresponder",
    "trigger": "subscription",
    "tenant": "client-1"
  }'

# 3. Email-Engine injecte dans MailWizz
# → POST https://sos-holidays.com/api/templates
# → POST https://sos-holidays.com/api/campaigns
```

**Résultat** : Templates/campagnes créés from scratch via API

---

## 📊 COMPARAISON FINALE

| Aspect | backup-cold (V1) | Email-Engine (V2) |
|--------|------------------|-------------------|
| **Templates** | 106 (existants) | 0 (à créer via API) |
| **Campagnes** | 77 (existantes) | 0 (à créer via API) |
| **MailWizz** | Version 2.2.11 avec données | Version latest vierge |
| **MySQL** | Base pleine | Base vide (structure seule) |
| **PowerMTA config** | 2 IPs backup-cold | 5 IPs neuves |
| **Domaines** | client2-domain.com, client1-domain.com | domain1-5.com (nouveaux) |
| **IPs** | 178.18.243.7, 84.247.168.78 | 5 IPs nouvelles |
| **Statut** | Archive (éteint) | Production (actif) |
| **Usage** | Référence historique | Système moderne |

---

## ✅ AVANTAGES SÉPARATION

### Pourquoi 2 systèmes distincts ?

**1. Indépendance** :
- V1 reste intact (backup safe)
- V2 peut évoluer librement
- Pas de dépendances croisées

**2. Clarté** :
- backup-cold = historique
- Email-Engine = futur
- Pas de confusion

**3. Flexibilité** :
- V2 peut avoir structure différente
- Templates V2 adaptés aux nouveaux besoins
- Campagnes V2 optimisées

**4. Sécurité** :
- Si V2 casse, V1 intact
- Rollback possible vers V1
- 2 systèmes = redondance

---

## 🎯 CE QU'ON GARDE DE BACKUP-COLD

```
backup-source/
├── ✅ pmta-license-20260216          (Licence perpétuelle)
│   └── Réutilisée dans V2
│
├── ✅ pmta-config-20260216            (Structure config)
│   └── Inspirée pour config V2 (adaptée 5 IPs)
│
├── ❌ mailwizz-prod-20260216.tar.gz  (PAS UTILISÉ)
│   └── Templates/campagnes V1 restent dans V1
│
└── ❌ mailapp-prod-20260216.sql.gz   (PAS UTILISÉ)
    └── Données V1 restent dans V1
```

---

## 🚀 WORKFLOW V2

```
1. Nouveau contact arrive
   ↓
2. Email-Engine API valide/stocke
   ↓
3. Email-Engine détermine : besoin template "welcome"
   ↓
4. Email-Engine cherche template dans PostgreSQL
   ↓ Si existe : utilise
   ↓ Si n'existe pas : crée via API
   ↓
5. Email-Engine injecte dans MailWizz V2
   ↓
6. MailWizz V2 (vide au départ) reçoit template + contact
   ↓
7. MailWizz déclenche campagne
   ↓
8. PowerMTA V2 envoie (5 IPs)
```

**Tout créé dynamiquement, rien migré de V1**

---

## 📝 RÉSUMÉ

### backup-cold (V1)
- ✅ Système complet intact
- ✅ 106 templates restent là-bas
- ✅ 77 campagnes restent là-bas
- ✅ Archive/référence
- ❌ Ne touche pas Email-Engine

### Email-Engine (V2)
- ✅ Système nouveau vierge
- ✅ MailWizz vide au départ
- ✅ Templates créés via API
- ✅ Campagnes créées via API
- ❌ Pas de migration V1

### Lien entre les 2
- ✅ Licence PowerMTA (réutilisée)
- ✅ Structure config PowerMTA (adaptée)
- ❌ Aucun autre lien

---

**Document créé le** : 16 février 2026 18:45
**Statut** : ✅ Clarification séparation systèmes
**Principe** : 2 systèmes TOTALEMENT distincts
