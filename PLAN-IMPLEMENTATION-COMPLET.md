# 🚀 PLAN D'IMPLÉMENTATION COMPLET - email-engine

**Date** : 16 février 2026
**Objectif** : Liste EXACTE de ce qu'il faut implémenter/configurer

---

## 📊 ARCHITECTURE FINALE

```
┌─────────────────────────────────────────┐
│   VPS 1: email-engine                   │
│   IP: 46.225.171.192 (Nuremberg)        │
│   Rôle: ORCHESTRATEUR                   │
│                                         │
│   ✅ DÉJÀ DÉPLOYÉ                       │
│   - FastAPI + PostgreSQL + Celery       │
│   - Warmup engine                       │
│   - Blacklist checker                   │
│   - DNS validator                       │
│   - API REST                            │
└────────────┬────────────────────────────┘
             │
             │ API calls
             ↓
┌─────────────────────────────────────────┐
│   VPS 2: MailWizz                       │
│   Domain: sos-holidays.com              │
│   Rôle: EMAIL MARKETING PLATFORM        │
│                                         │
│   ⏳ À INSTALLER                        │
│   - MailWizz (PHP application)          │
│   - MySQL database                      │
│   - Apache/Nginx                        │
│   - API configurée                      │
└────────────┬────────────────────────────┘
             │
             │ SMTP sending
             ↓
┌─────────────────────────────────────────┐
│   VPS 3: PowerMTA                       │
│   IPs: 5 IPs dédiées (à acheter)       │
│   Domains: 5 domaines (à configurer)    │
│   Rôle: SMTP ENGINE                     │
│                                         │
│   ⏳ À INSTALLER + CONFIGURER           │
│   - PowerMTA                            │
│   - 5 VirtualMTAs                       │
│   - DKIM keys (5 domaines)              │
│   - SPF/DMARC records                   │
└─────────────────────────────────────────┘
```

---

## ✅ CE QUI EST DÉJÀ FAIT (email-engine)

### VPS 1: email-engine (46.225.171.192)

```
✅ Infrastructure
   ├─ PostgreSQL 15 (base de données)
   ├─ Redis 7 (cache + Celery broker)
   ├─ Celery workers (4 workers + beat)
   ├─ FastAPI application
   └─ Migrations alembic (3 migrations appliquées)

✅ Code Backend
   ├─ app/ (legacy layer)
   │   ├─ IP management (CRUD)
   │   ├─ Warmup plans
   │   ├─ Blacklist checking (9 RBL)
   │   ├─ DNS validation (SPF/DKIM/DMARC/PTR)
   │   └─ API routes (/health, /ips, /warmup, etc.)
   │
   └─ src/ (clean architecture) - STRUCTURE PRÊTE

✅ Features Implémentées
   ├─ JWT Authentication
   ├─ Role-Based Access Control (RBAC)
   ├─ Audit logging
   ├─ Health checks
   ├─ Structured logging (JSON)
   └─ API documentation (Swagger UI)

✅ Monitoring (partiel)
   ├─ Prometheus metrics endpoint
   └─ Health check endpoint
```

---

## ❌ CE QUI MANQUE (À IMPLÉMENTER)

### 1. Dans email-engine (Code Python)

#### A. MailWizz Client (URGENT - Priorité 1)

**Fichier** : `src/infrastructure/external/mailwizz_client.py`

**Status** : ⚠️ EXISTE mais incomplet

**Ce qui manque** :

```python
class MailWizzClient:
    """Client pour interagir avec API MailWizz."""

    # ✅ EXISTE (à vérifier/compléter)
    def __init__(self, api_url, public_key, private_key):
        pass

    # ❌ MANQUE - CRITICAL
    def create_delivery_server(
        self,
        name: str,
        hostname: str,
        port: int,
        username: str,
        password: str,
        quota_daily: int,
        vmta_header: str
    ) -> dict:
        """
        POST /api/delivery-servers
        Crée un delivery server dans MailWizz

        Body:
        {
          "server": {
            "type": "smtp",
            "name": "SMTP Cold IP1",
            "hostname": "46.x.x.x",
            "port": 587,
            "username": "mailwizz",
            "password": "...",
            "protocol": "tls",
            "timeout": 30,
            "from_email": "noreply@sos-mail.com",
            "from_name": "SOS Expat",
            "quota_daily": 50,
            "additional_headers": [
              {
                "name": "X-Virtual-MTA",
                "value": "pmta-vmta0"
              }
            ]
          }
        }
        """
        pass

    # ❌ MANQUE - CRITICAL
    def update_delivery_server_quota(
        self,
        server_id: str,
        quota_daily: int
    ) -> dict:
        """
        PATCH /api/delivery-servers/{server_id}
        Update quota d'un delivery server

        Utilisé par warmup engine pour ajuster quotas automatiquement
        """
        pass

    # ❌ MANQUE - CRITICAL
    def create_campaign(
        self,
        list_id: str,
        segment_id: str,
        template_id: str,
        subject: str,
        from_name: str,
        from_email: str,
        reply_to: str
    ) -> dict:
        """
        POST /api/campaigns
        Crée une campagne dans MailWizz
        """
        pass

    # ❌ MANQUE - IMPORTANT
    def get_campaign_stats(self, campaign_id: str) -> dict:
        """
        GET /api/campaigns/{campaign_id}/stats
        Récupère stats campagne (sent, opens, clicks, bounces)
        """
        pass

    # ❌ MANQUE - IMPORTANT
    def import_subscribers(
        self,
        list_id: str,
        subscribers: list[dict]
    ) -> dict:
        """
        POST /api/lists/{list_id}/subscribers
        Importe contacts dans une liste MailWizz

        subscribers = [
          {
            "EMAIL": "contact@example.com",
            "FNAME": "John",
            "LNAME": "Doe",
            "COUNTRY": "France"
          }
        ]
        """
        pass

    # ❌ MANQUE - OPTIONNEL
    def create_list(
        self,
        name: str,
        description: str,
        from_name: str,
        from_email: str
    ) -> dict:
        """
        POST /api/lists
        Crée une liste dans MailWizz
        """
        pass
```

**Action** :
```bash
# Compléter le fichier existant
vim src/infrastructure/external/mailwizz_client.py

# Ou créer nouveau client complet
vim src/infrastructure/external/mailwizz_api_client.py
```

#### B. PowerMTA Config Generator (URGENT - Priorité 1)

**Fichier** : `src/infrastructure/external/powermta_config_generator.py`

**Status** : ⚠️ EXISTE mais basique

**Ce qui manque** :

```python
class PowerMTAConfigGenerator:
    """Génère configuration PowerMTA dynamiquement."""

    # ❌ MANQUE - CRITICAL
    def generate_config(
        self,
        ips: list[IP],
        domains: list[Domain]
    ) -> str:
        """
        Génère config PowerMTA complète

        Template:
        ################################
        # POWERMTA CONFIG - AUTO-GENERATED
        ################################

        postmaster admin@sos-mail.com
        host-name mail.sos-mail.com

        # SMTP Listeners
        smtp-listener {ip1}:2525
        smtp-listener {ip2}:2525
        ...

        # SMTP Auth
        <smtp-user mailwizz@sos-mail.com>
            password {PASSWORD}
            source {pmta-auth}
        </smtp-user>

        # VirtualMTAs
        <virtual-mta pmta-vmta0>
            smtp-source-host {ip1} mail1.sos-mail.com
            domain-key dkim,*,/home/pmta/conf/mail/sos-mail.com/dkim.pem
            <domain *>
                max-cold-virtual-mta-msg {quota}/day
                max-msg-rate 1000/h
            </domain>
        </virtual-mta>
        ...

        # VirtualMTA Pool
        <virtual-mta-pool pmta-pool>
            virtual-mta pmta-vmta0
            virtual-mta pmta-vmta1
            ...
        </virtual-mta-pool>

        # ISP Rate Limits (hotmail, gmail, yahoo, etc.)
        ...

        # Bounce Rules
        ...
        """
        pass

    # ❌ MANQUE - CRITICAL
    def deploy_config(
        self,
        config: str,
        pmta_host: str,
        pmta_port: int = 22
    ) -> bool:
        """
        1. SSH sur serveur PowerMTA
        2. Backup config actuelle
        3. Write nouvelle config
        4. Validate syntax (pmta validate)
        5. Reload PowerMTA (pmta reload)
        6. Si erreur → Rollback
        """
        pass

    # ❌ MANQUE - IMPORTANT
    def generate_dkim_key(
        self,
        domain: str,
        selector: str = "default"
    ) -> tuple[str, str]:
        """
        Génère paire de clés DKIM (privée + publique)

        Returns:
            (private_key_pem, dns_record_txt)

        private_key_pem → /home/pmta/conf/mail/{domain}/dkim.pem
        dns_record_txt → TXT record pour {selector}._domainkey.{domain}
        """
        pass
```

**Action** :
```bash
vim src/infrastructure/external/powermta_config_generator.py
```

#### C. Campaign Orchestrator (IMPORTANT - Priorité 2)

**Fichier** : `src/application/use_cases/create_campaign.py`

**Status** : ❌ N'EXISTE PAS

**Ce qui manque** :

```python
class CreateCampaignUseCase:
    """Orchestrate création campagne cold email."""

    def execute(
        self,
        tenant_id: int,
        name: str,
        contacts: list[dict],
        template_id: str,
        schedule: dict
    ) -> Campaign:
        """
        1. Valider contacts (email syntax, MX, SMTP)
        2. Importer contacts dans MailWizz
        3. Sélectionner IPs disponibles (status=ACTIVE, non-blacklistées)
        4. Calculer quotas (respecter warmup)
        5. Créer campagne dans MailWizz
        6. Scheduler envoi
        7. Monitorer métriques (bounce/complaint rates)
        """

        # 1. Validation contacts
        validated = self._validate_contacts(contacts)

        # 2. Import MailWizz
        mailwizz_list_id = self._import_to_mailwizz(validated)

        # 3. Sélectionner IPs
        available_ips = self._select_available_ips(tenant_id)

        # 4. Calculer quotas
        quotas = self._calculate_quotas(available_ips)

        # 5. Créer campagne MailWizz
        campaign_id = self._create_mailwizz_campaign(
            mailwizz_list_id,
            template_id,
            schedule
        )

        # 6. Enregistrer dans DB
        campaign = Campaign(
            tenant_id=tenant_id,
            name=name,
            mailwizz_campaign_id=campaign_id,
            status="scheduled"
        )
        db.add(campaign)
        db.commit()

        return campaign
```

**Action** :
```bash
mkdir -p src/application/use_cases
vim src/application/use_cases/create_campaign.py
```

#### D. Contact Validator (IMPORTANT - Priorité 2)

**Fichier** : `src/domain/services/contact_validator.py`

**Status** : ❌ N'EXISTE PAS

**Ce qui manque** :

```python
class ContactValidator:
    """Valide emails avant envoi."""

    def validate_email(self, email: str) -> ValidationResult:
        """
        Validation en 3 niveaux:

        1. Syntax (regex)
        2. MX Record (DNS query)
        3. SMTP Check (tentative connexion VRFY)

        Returns:
            ValidationResult(
                valid: bool,
                reason: str,
                confidence: float  # 0.0 - 1.0
            )
        """

        # 1. Syntax
        if not self._validate_syntax(email):
            return ValidationResult(False, "invalid_syntax", 0.0)

        # 2. MX Record
        mx_records = self._check_mx_record(email.split('@')[1])
        if not mx_records:
            return ValidationResult(False, "no_mx_record", 0.0)

        # 3. SMTP Check (optionnel, peut être lent)
        if self.deep_validation:
            smtp_valid = self._smtp_verify(email, mx_records[0])
            if not smtp_valid:
                return ValidationResult(False, "smtp_check_failed", 0.5)

        return ValidationResult(True, "valid", 1.0)
```

**Action** :
```bash
mkdir -p src/domain/services
vim src/domain/services/contact_validator.py
```

#### E. API Routes Campaign (IMPORTANT - Priorité 2)

**Fichier** : `app/api/routes/campaigns.py`

**Status** : ❌ N'EXISTE PAS

**Ce qui manque** :

```python
from fastapi import APIRouter, Depends, UploadFile

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])

@router.post("/", status_code=201)
def create_campaign(
    payload: CreateCampaignRequest,
    db: Session = Depends(get_db)
):
    """Créer campagne cold email."""
    pass

@router.post("/import-csv")
async def import_contacts_csv(
    file: UploadFile,
    tenant_id: int,
    db: Session = Depends(get_db)
):
    """Upload CSV contacts pour campagne."""
    # Parse CSV
    # Valider contacts
    # Stocker dans DB
    pass

@router.get("/{campaign_id}/stats")
def get_campaign_stats(campaign_id: int, db: Session = Depends(get_db)):
    """Récupérer stats campagne."""
    pass
```

**Action** :
```bash
vim app/api/routes/campaigns.py
```

#### F. Webhook Handlers (OPTIONNEL - Priorité 3)

**Fichier** : `app/api/routes/webhooks.py`

**Status** : ⚠️ EXISTE (vide)

**Ce qui manque** :

```python
@router.post("/scraper-pro")
async def scraper_pro_webhook(
    payload: dict,
    signature: str = Header(None)
):
    """
    Webhook depuis Scraper-Pro

    Reçoit contacts scrapés et les import automatiquement

    Payload:
    {
      "source": "linkedin_lawyers",
      "contacts": [
        {
          "email": "avocat@example.com",
          "first_name": "Jean",
          "last_name": "Dupont",
          "country": "France"
        }
      ]
    }
    """
    # Vérifier signature HMAC
    # Valider contacts
    # Import dans DB
    pass

@router.post("/backlinks-engine")
async def backlinks_engine_webhook(payload: dict):
    """Webhook depuis backlinks-engine."""
    pass

@router.post("/mailwizz-bounce")
async def mailwizz_bounce_webhook(payload: dict):
    """
    Webhook bounces depuis MailWizz

    Marquer contact comme bounced dans DB
    Si bounce rate > 5% → PAUSE campaign
    """
    pass
```

**Action** :
```bash
vim app/api/routes/webhooks.py
```

---

### 2. Sur VPS 2: MailWizz (sos-holidays.com)

#### A. Installation MailWizz (URGENT - Priorité 1)

**Actions** :

```bash
# 1. Préparer VPS
apt update && apt upgrade -y
apt install -y nginx mysql-server php8.1 php8.1-{cli,mysql,mbstring,xml,curl,zip,gd,intl}

# 2. Télécharger MailWizz
cd /var/www
wget https://www.mailwizz.com/downloads/mailwizz-latest.zip
unzip mailwizz-latest.zip
chown -R www-data:www-data /var/www/mailwizz

# 3. Créer base MySQL
mysql -u root -p
CREATE DATABASE mailwizz;
CREATE USER 'mailwizz'@'localhost' IDENTIFIED BY 'STRONG_PASSWORD';
GRANT ALL PRIVILEGES ON mailwizz.* TO 'mailwizz'@'localhost';
FLUSH PRIVILEGES;

# 4. Configurer Nginx
cat > /etc/nginx/sites-available/mailwizz << 'EOF'
server {
    listen 80;
    server_name sos-holidays.com www.sos-holidays.com;
    root /var/www/mailwizz;
    index index.php;

    location / {
        try_files $uri $uri/ /index.php?$query_string;
    }

    location ~ \.php$ {
        fastcgi_pass unix:/var/run/php/php8.1-fpm.sock;
        fastcgi_index index.php;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        include fastcgi_params;
    }

    client_max_body_size 100M;
}
EOF

ln -s /etc/nginx/sites-available/mailwizz /etc/nginx/sites-enabled/
systemctl restart nginx

# 5. Installer SSL
certbot --nginx -d sos-holidays.com -d www.sos-holidays.com

# 6. Accéder wizard installation
https://sos-holidays.com/index.php/setup
```

#### B. Configuration MailWizz (URGENT - Priorité 1)

**Actions après installation** :

1. **Créer Customer (Tenant)**
   - Backend → Customers → Create new
   - Customer 1: SOS-Expat
   - Customer 2: Ulixai

2. **Générer API Keys**
   - Backend → Settings → API Keys
   - Enable API
   - Generate keys pour chaque customer
   - Noter les clés (public + private)

3. **Créer Listes**
   - Customer SOS-Expat → Lists → Create
     - Liste: "Cold Outreach Avocats"
     - Liste: "Cold Outreach Notaires"
   - Customer Ulixai → Lists → Create
     - Liste: "Cold Outreach Bloggers"

4. **Créer Templates**
   - Templates → Create
   - Template: "Cold Outreach v1"
   - Utiliser tags: [FNAME], [LNAME], [COMPANY]

5. **Configurer Delivery Servers** (APRÈS config PowerMTA)
   - Backend → Delivery Servers → Create SMTP
   - Pour CHAQUE IP PowerMTA:
     ```
     Name: SMTP Cold IP1
     Hostname: {POWERMTA_VPS_IP}
     Port: 587
     Username: mailwizz
     Password: {PMTA_PASSWORD}
     Protocol: TLS
     From Email: noreply@sos-mail.com
     Daily Quota: 50 (warmup start)
     Additional Headers:
       X-Virtual-MTA: pmta-vmta0
     ```

#### C. Configuration .env email-engine

**Fichier** : `/opt/email-engine/.env` (sur VPS 1)

**Ajouter** :

```bash
# MailWizz API
MAILWIZZ_API_URL=https://sos-holidays.com/api
MAILWIZZ_API_PUBLIC_KEY={CLÉ_PUBLIQUE_MAILWIZZ}
MAILWIZZ_API_PRIVATE_KEY={CLÉ_PRIVÉE_MAILWIZZ}

# Customer-specific API keys
MAILWIZZ_SOS_API_KEY={CLÉ_CUSTOMER_SOS_EXPAT}
MAILWIZZ_ULIXAI_API_KEY={CLÉ_CUSTOMER_ULIXAI}
```

---

### 3. Sur VPS 3: PowerMTA

#### A. Acheter IPs + Domaines (URGENT - Priorité 1)

**IPs nécessaires** :

```
5 IPs dédiées
  ├─ IP1: X.X.X.1 (mail1.sos-mail.com)
  ├─ IP2: X.X.X.2 (mail2.sos-mail.com)
  ├─ IP3: X.X.X.3 (mail3.sos-mail.com)
  ├─ IP4: X.X.X.4 (mail4.sos-mail.com)
  └─ IP5: X.X.X.5 (mail5.sos-mail.com)

Provider recommandé: Hetzner Cloud (bon pour IPs clean)
```

**Domaines nécessaires** :

```
5 domaines dédiés COLD EMAIL (PAS les brand domains!)
  ├─ sos-mail.com
  ├─ ulixai-mail.com
  ├─ expat-services.com
  ├─ expat-connect.com
  └─ global-expat.com

Important: WHOIS Privacy activé (éviter footprint)
```

#### B. Installation PowerMTA (URGENT - Priorité 1)

**Actions** :

```bash
# 1. Télécharger PowerMTA (depuis ton compte)
cd /tmp
wget {URL_POWERMTA_FROM_YOUR_ACCOUNT}
tar -xzf pmta-*.tar.gz
cd pmta-*/

# 2. Installer
./install.sh

# 3. Copier licence
cp /path/to/pmta-license /etc/pmta/license

# 4. Générer DKIM keys (pour chaque domaine)
mkdir -p /home/pmta/conf/mail

for domain in sos-mail.com ulixai-mail.com expat-services.com expat-connect.com global-expat.com
do
    mkdir -p /home/pmta/conf/mail/$domain
    openssl genrsa -out /home/pmta/conf/mail/$domain/dkim.pem 2048
    openssl rsa -in /home/pmta/conf/mail/$domain/dkim.pem -pubout -outform PEM
    # Note la clé publique pour DNS
done

# 5. Créer config initiale
cat > /etc/pmta/config << 'EOF'
# Config générée par email-engine
# Ne PAS éditer manuellement

postmaster admin@sos-mail.com
host-name mail.sos-mail.com

# SMTP Listeners (toutes les IPs)
smtp-listener X.X.X.1:2525
smtp-listener X.X.X.2:2525
smtp-listener X.X.X.3:2525
smtp-listener X.X.X.4:2525
smtp-listener X.X.X.5:2525

# SMTP Auth
<smtp-user mailwizz@sos-mail.com>
    password STRONG_PASSWORD_HERE
    source {pmta-auth}
</smtp-user>

<source {pmta-auth}>
    smtp-service yes
    always-allow-relaying yes
    require-auth true
    process-x-virtual-mta yes
    default-virtual-mta pmta-pool
</source>

# VirtualMTAs (1 par IP)
<virtual-mta pmta-vmta0>
    smtp-source-host X.X.X.1 mail1.sos-mail.com
    domain-key dkim,*,/home/pmta/conf/mail/sos-mail.com/dkim.pem
    <domain *>
        max-cold-virtual-mta-msg 50/day
        max-msg-rate 1000/h
    </domain>
</virtual-mta>

# Répéter pour vmta1-4...

# Pool
<virtual-mta-pool pmta-pool>
    virtual-mta pmta-vmta0
    virtual-mta pmta-vmta1
    virtual-mta pmta-vmta2
    virtual-mta pmta-vmta3
    virtual-mta pmta-vmta4
</virtual-mta-pool>

# ISP Rate Limits
<domain $hotmail>
    max-msg-rate 250/h
</domain>

# etc...
EOF

# 6. Démarrer PowerMTA
systemctl start pmta
systemctl enable pmta

# 7. Vérifier status
pmta status
```

#### C. Configuration DNS (URGENT - Priorité 1)

**Pour CHAQUE domaine** :

1. **SPF Record**
   ```
   Type: TXT
   Name: @
   Value: v=spf1 ip4:X.X.X.1 ip4:X.X.X.2 ip4:X.X.X.3 ip4:X.X.X.4 ip4:X.X.X.5 ~all
   ```

2. **DKIM Record** (pour chaque domaine)
   ```
   Type: TXT
   Name: default._domainkey
   Value: v=DKIM1; k=rsa; p={PUBLIC_KEY_FROM_OPENSSL}
   ```

3. **DMARC Record**
   ```
   Type: TXT
   Name: _dmarc
   Value: v=DMARC1; p=quarantine; rua=mailto:dmarc@sos-mail.com
   ```

4. **MX Record**
   ```
   Type: MX
   Name: @
   Priority: 10
   Value: mail.sos-mail.com
   ```

5. **PTR (Reverse DNS)** - Pour CHAQUE IP
   ```
   Chez ton provider (Hetzner):
   X.X.X.1 → mail1.sos-mail.com
   X.X.X.2 → mail2.sos-mail.com
   etc...
   ```

---

## 📋 CHECKLIST IMPLÉMENTATION

### Phase 1: Infrastructure (Semaine 1)

- [ ] **VPS 2 (MailWizz)** - Acheter + installer
  - [ ] Acheter VPS (2 vCPU, 4GB RAM min)
  - [ ] Installer MailWizz
  - [ ] Configurer SSL (sos-holidays.com)
  - [ ] Créer customers (SOS-Expat, Ulixai)
  - [ ] Générer API keys
  - [ ] Noter clés dans email-engine .env

- [ ] **VPS 3 (PowerMTA)** - Acheter + installer
  - [ ] Acheter VPS (4 vCPU, 8GB RAM min)
  - [ ] Acheter 5 IPs dédiées
  - [ ] Acheter 5 domaines (WHOIS privacy)
  - [ ] Installer PowerMTA
  - [ ] Générer DKIM keys (5 domaines)
  - [ ] Configurer DNS (SPF/DKIM/DMARC/MX/PTR)

### Phase 2: Code (Semaine 2)

- [ ] **email-engine - MailWizz Client**
  - [ ] Compléter `mailwizz_client.py`
  - [ ] `create_delivery_server()`
  - [ ] `update_delivery_server_quota()`
  - [ ] `create_campaign()`
  - [ ] `import_subscribers()`
  - [ ] Tests unitaires

- [ ] **email-engine - PowerMTA Generator**
  - [ ] Compléter `powermta_config_generator.py`
  - [ ] `generate_config()`
  - [ ] `deploy_config()` (SSH)
  - [ ] `generate_dkim_key()`
  - [ ] Tests unitaires

- [ ] **email-engine - Campaign Orchestrator**
  - [ ] Créer `create_campaign.py` use case
  - [ ] Validation contacts
  - [ ] Sélection IPs
  - [ ] Création campagne MailWizz
  - [ ] Tests unitaires

- [ ] **email-engine - Contact Validator**
  - [ ] Créer `contact_validator.py`
  - [ ] Validation syntax
  - [ ] Check MX record
  - [ ] SMTP verification
  - [ ] Tests unitaires

- [ ] **email-engine - API Routes**
  - [ ] Créer `/api/v2/campaigns` routes
  - [ ] POST /campaigns
  - [ ] POST /campaigns/import-csv
  - [ ] GET /campaigns/{id}/stats
  - [ ] Tests API

### Phase 3: Intégration (Semaine 3)

- [ ] **MailWizz ↔ email-engine**
  - [ ] Créer delivery servers via API
  - [ ] Sync quotas warmup → MailWizz
  - [ ] Test création campagne end-to-end

- [ ] **PowerMTA ↔ email-engine**
  - [ ] Générer config PowerMTA
  - [ ] Deploy config (SSH)
  - [ ] Reload PowerMTA
  - [ ] Test envoi SMTP

- [ ] **Scraper-Pro → email-engine**
  - [ ] Webhook handler
  - [ ] Import contacts automatique
  - [ ] Test import CSV

### Phase 4: Warmup (Semaines 4-9)

- [ ] **Lancer warmup 5 IPs**
  - [ ] Semaine 4: 50/jour × 5 IPs = 250/jour
  - [ ] Semaine 5: 200/jour × 5 = 1000/jour
  - [ ] Semaine 6: 500/jour × 5 = 2500/jour
  - [ ] Semaine 7: 1500/jour × 5 = 7500/jour
  - [ ] Semaine 8: 5000/jour × 5 = 25,000/jour
  - [ ] Semaine 9: 10,000/jour × 5 = 50,000/jour

### Phase 5: Production (Semaine 10+)

- [ ] **Première campagne cold**
  - [ ] Import 10,000 contacts (Scraper-Pro)
  - [ ] Validation contacts
  - [ ] Création campagne
  - [ ] Envoi 50,000 emails
  - [ ] Monitoring metrics

- [ ] **Scaling**
  - [ ] Acheter 10 IPs supplémentaires
  - [ ] Warmup parallèle (6 semaines)
  - [ ] Target: 100,000 emails/jour (10 IPs × 10k)

---

## 💰 BUDGET ESTIMATIF

```
VPS 2 (MailWizz):
  Hetzner CPX21 (2 vCPU, 4GB RAM): 8.49€/mois

VPS 3 (PowerMTA):
  Hetzner CCX23 (4 vCPU, 8GB RAM): 24.49€/mois
  + 5 IPs supplémentaires: 5 × 1€ = 5€/mois
  Total: 29.49€/mois

Domaines (5 domaines):
  5 × 10€/an = 50€/an (4.17€/mois)

Licences:
  PowerMTA: (déjà acheté)
  MailWizz: (déjà acheté)

TOTAL MENSUEL: 8.49 + 29.49 + 4.17 = 42.15€/mois
TOTAL ANNUEL: 506€/an
```

---

## ⏱️ TIMELINE

```
Semaine 1: Infrastructure
  ├─ Jour 1-2: Acheter VPS 2 + 3, domaines, IPs
  ├─ Jour 3-4: Installer MailWizz
  ├─ Jour 5: Installer PowerMTA
  ├─ Jour 6: Configurer DNS (SPF/DKIM/DMARC)
  └─ Jour 7: Tests connexion MailWizz ↔ PowerMTA

Semaine 2: Développement
  ├─ Jour 1-2: MailWizz Client (Python)
  ├─ Jour 3-4: PowerMTA Generator (Python)
  ├─ Jour 5-6: Campaign Orchestrator (Python)
  └─ Jour 7: Tests unitaires

Semaine 3: Intégration
  ├─ Jour 1-2: email-engine ↔ MailWizz
  ├─ Jour 3-4: email-engine ↔ PowerMTA
  ├─ Jour 5-6: Scraper-Pro → email-engine
  └─ Jour 7: Tests end-to-end

Semaines 4-9: Warmup IPs (6 semaines)
  └─ Automatique (email-engine gère)

Semaine 10+: Production
  └─ Lancer campagnes cold (50k emails/jour)
```

---

## 🎯 PROCHAINES ACTIONS IMMÉDIATES

**Tu es prêt à commencer ? Voici l'ordre recommandé :**

1. **AUJOURD'HUI** :
   - [ ] Acheter VPS 2 (MailWizz)
   - [ ] Acheter VPS 3 (PowerMTA)
   - [ ] Acheter 5 IPs dédiées
   - [ ] Acheter 5 domaines (+ WHOIS privacy)

2. **DEMAIN** :
   - [ ] Installer MailWizz (VPS 2)
   - [ ] Installer PowerMTA (VPS 3)
   - [ ] Configurer DNS (tous les domaines)

3. **APRÈS-DEMAIN** :
   - [ ] Je t'aide à implémenter le code Python manquant
   - [ ] Tests intégration
   - [ ] Lancer warmup

**Tu veux que je t'aide pour quelle étape en premier ?**
