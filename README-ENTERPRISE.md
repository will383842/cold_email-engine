# Email Engine - Enterprise Multi-Tenant Architecture

## 📋 Vue d'ensemble

Architecture enterprise Clean/Hexagonal pour un système d'email marketing multi-tenant avec:

- ✅ **2 Tenants** - SOS-Expat et Ulixai (isolation complète)
- ✅ **Multi-sources** - Scraper-Pro, Backlink Engine, CSV, API webhooks
- ✅ **100 IPs rotatifs** - 50 par tenant avec warmup automatique
- ✅ **100 domaines d'envoi** - 1 par IP (séparé des domaines de marque)
- ✅ **9 langues** - FR, EN, ES, DE, PT, RU, ZH, HI, AR + fallback anglais
- ✅ **Tag-based segmentation** - Filtres AND/OR/EXCLUDE
- ✅ **Clean Architecture** - Domain, Application, Infrastructure, Presentation

---

## 🏗️ Architecture

### Structure des dossiers

```
email-engine/
├── app/                          # 🔵 API v1 - Code existant (IPs, warmup, DNS)
│   ├── api/routes/               # Routes API v1
│   ├── services/                 # Services existants
│   ├── models.py                 # SQLAlchemy models (mis à jour)
│   ├── enums.py                  # Enums (mis à jour)
│   └── main.py                   # FastAPI app
│
├── src/                          # 🟢 Architecture Clean (NOUVEAU)
│   ├── domain/                   # Couche Domain (Business Logic)
│   │   ├── entities/             # Contact, Campaign
│   │   ├── value_objects/        # Email, Language, TagSlug
│   │   ├── services/             # ContactValidator, TemplateSelector
│   │   ├── events/               # ContactIngested, CampaignLaunched
│   │   └── repositories/         # IContactRepository, ICampaignRepository (interfaces)
│   │
│   ├── application/              # Couche Application (Use Cases)
│   │   ├── use_cases/            # IngestContactsUseCase, CreateCampaignUseCase
│   │   ├── dto/                  # Data Transfer Objects
│   │   └── mappers/              # Entity ↔ DTO mappers
│   │
│   ├── infrastructure/           # Couche Infrastructure (Adapters)
│   │   ├── persistence/          # SQLAlchemyContactRepository
│   │   ├── cache/                # Redis cache
│   │   ├── messaging/            # RabbitMQ/Redis queue
│   │   ├── external/             # MailWizz, PowerMTA clients
│   │   └── background/           # Celery tasks
│   │
│   └── presentation/             # Couche Presentation (API v2)
│       └── api/v2/               # Contacts, Campaigns, Templates endpoints
│
├── scripts/                      # Scripts utilitaires
│   ├── seed_enterprise_data.py   # Seed 100 IPs + 100 domaines
│   └── manage-users.py           # Gestion utilisateurs
│
├── alembic/                      # Database migrations
│   └── versions/
│       ├── 001_initial.py        # IPs, domains, warmup
│       ├── 002_add_auth.py       # Auth, audit
│       └── 003_enterprise.py     # 🆕 Multi-tenant tables
│
└── docs/                         # Documentation architecture
    ├── ARCHITECTURE-ENTERPRISE.md
    ├── ARCHITECTURE-INFRASTRUCTURE.md
    └── ARCHITECTURE-MULTI-SOURCES.md
```

---

## 🗄️ Schéma de base de données

### Nouvelles tables (migration 003)

```sql
-- Tenants (SOS-Expat, Ulixai)
tenants (id, slug, name, brand_domain, sending_domain_base, is_active)

-- Sources de données
data_sources (id, tenant_id, name, type, config, is_active, total_contacts_ingested)

-- Tags (système hiérarchique)
tags (id, tenant_id, slug, label, parent_id, color, description)

-- Contacts (prospects)
contacts (
  id, tenant_id, data_source_id, email, first_name, last_name, company, website,
  language, category, phone, country, city, linkedin_url, facebook_url, instagram_url,
  twitter_url, custom_fields, status, validation_status, validation_score,
  mailwizz_subscriber_id, mailwizz_list_id, last_campaign_sent_at, total_campaigns_received
)

-- Contact-Tags (many-to-many)
contact_tags (id, contact_id, tag_id, added_at)

-- Templates email (9 langues + catégorie)
email_templates (
  id, tenant_id, name, language, category, subject, body_html, body_text,
  variables, is_default, total_sent, avg_open_rate, avg_click_rate
)

-- Campagnes
campaigns (
  id, tenant_id, name, status, template_id, language, category,
  tags_all, tags_any, exclude_tags, total_recipients, sent_count, delivered_count,
  opened_count, clicked_count, bounced_count, unsubscribed_count,
  scheduled_at, started_at, completed_at, mailwizz_campaign_id
)

-- Events contact (audit trail)
contact_events (
  id, contact_id, campaign_id, event_type, event_data, timestamp
)

-- Instances MailWizz
mailwizz_instances (
  id, tenant_id, name, base_url, api_public_key, api_private_key,
  default_list_id, is_active, last_health_check
)
```

### Tables existantes (mises à jour)

```sql
-- Ajout tenant_id aux IPs et domaines
ips.tenant_id         -- NULL pour IPs existants, puis assigné lors du seed
domains.tenant_id     -- NULL pour domaines existants, puis assigné lors du seed
```

---

## 🚀 Migration et déploiement

### 1. Appliquer la migration

```bash
cd email-engine

# Créer la migration
alembic upgrade head

# Vérifier
alembic current
```

### 2. Seed des données enterprise

```bash
# Créer les 2 tenants + 100 IPs + 100 domaines + 2 instances MailWizz
python scripts/seed_enterprise_data.py
```

**Résultat:**
- ✅ 2 Tenants (SOS-Expat, Ulixai)
- ✅ 100 IPs (50 par tenant)
  - SOS-Expat: `45.123.10.1-50`
  - Ulixai: `45.124.20.1-50`
- ✅ 100 Domaines (1 par IP)
  - SOS-Expat: `mail1.sos-mail.com` → `mail50.sos-mail.com`
  - Ulixai: `mail1.ulixai-mail.com` → `mail50.ulixai-mail.com`
- ✅ 2 instances MailWizz
- ✅ 16 tags de base (SOS-Expat)

### 3. Configuration post-seed

#### A. Mettre à jour les clés API MailWizz

```sql
UPDATE mailwizz_instances
SET api_public_key = 'VOTRE_CLE_PUBLIQUE',
    api_private_key = 'VOTRE_CLE_PRIVEE'
WHERE tenant_id = 1;  -- SOS-Expat

UPDATE mailwizz_instances
SET api_public_key = 'VOTRE_CLE_PUBLIQUE',
    api_private_key = 'VOTRE_CLE_PRIVEE'
WHERE tenant_id = 2;  -- Ulixai
```

#### B. Configurer DNS (SPF, DKIM, DMARC, PTR)

Pour chaque domaine, configurer:

```dns
# SPF
mail1.sos-mail.com.  TXT  "v=spf1 ip4:45.123.10.1 -all"

# DKIM
default._domainkey.mail1.sos-mail.com.  TXT  "v=DKIM1; k=rsa; p=VOTRE_CLE_PUBLIQUE"

# DMARC
_dmarc.mail1.sos-mail.com.  TXT  "v=DMARC1; p=quarantine; rua=mailto:dmarc@sos-expat.com"

# PTR (reverse DNS)
1.10.123.45.in-addr.arpa.  PTR  mail1.sos-mail.com.
```

#### C. Configurer PowerMTA

Créer 100 VirtualMTAs (1 par IP):

```pmta
# Pool SOS-Expat
<VirtualMTA vmta-sos-expat-1>
    smtp-source-host mail1.sos-mail.com 45.123.10.1
</VirtualMTA>

<VirtualMTA vmta-sos-expat-2>
    smtp-source-host mail2.sos-mail.com 45.123.10.2
</VirtualMTA>

# ... (répéter pour les 50 IPs SOS-Expat)

# Pool Ulixai
<VirtualMTA vmta-ulixai-1>
    smtp-source-host mail1.ulixai-mail.com 45.124.20.1
</VirtualMTA>

# ... (répéter pour les 50 IPs Ulixai)
```

---

## 🔌 Utilisation de l'API v2

### Ingestion de contacts (Scraper-Pro, Backlink Engine, CSV)

**Endpoint:** `POST /api/v2/contacts/ingest`

**Exemple - Import CSV:**

```json
{
  "contacts": [
    {
      "tenant_id": 1,
      "data_source_id": 3,
      "email": "avocat1@example.fr",
      "first_name": "Pierre",
      "last_name": "Dupont",
      "company": "Cabinet Dupont",
      "website": "https://cabinet-dupont.fr",
      "language": "fr",
      "category": "avocat",
      "country": "FR",
      "city": "Paris",
      "tags": ["prestataire", "avocat", "lang-fr"]
    },
    {
      "tenant_id": 1,
      "data_source_id": 1,
      "email": "blogger1@example.es",
      "first_name": "Maria",
      "last_name": "Garcia",
      "website": "https://blog-expat-espagne.es",
      "language": "es",
      "category": "blogger",
      "country": "ES",
      "tags": ["marketing-partner", "blogger", "lang-es"]
    }
  ]
}
```

**Réponse:**

```json
{
  "success": true,
  "total_processed": 2,
  "new_contacts": 2,
  "updated_contacts": 0,
  "duplicates_skipped": 0,
  "errors": []
}
```

### Lister les contacts

**Endpoint:** `GET /api/v2/contacts/{tenant_id}?limit=100`

```bash
curl http://localhost:8000/api/v2/contacts/1?limit=50
```

### Récupérer un contact

**Endpoint:** `GET /api/v2/contacts/{tenant_id}/{contact_id}`

```bash
curl http://localhost:8000/api/v2/contacts/1/123
```

---

## 🏷️ Système de tags

### Tags SOS-Expat (créés par défaut)

```
Prestataires:
  ├── prestataire (parent)
  ├── avocat
  └── expat-aidant

Marketing Partners:
  ├── marketing-partner (parent)
  ├── blogger
  ├── influencer
  ├── chatter
  └── admin-group

Clients:
  ├── client (parent)
  ├── vacancier
  ├── expat
  └── digital-nomad

Langues:
  ├── lang-fr
  ├── lang-en
  ├── lang-es
  └── lang-de
```

### Segmentation par tags

**Exemple - Campagne pour avocats francophones:**

```json
{
  "tags_all": ["avocat", "lang-fr"],  // AND (avocat ET français)
  "tags_any": [],
  "exclude_tags": ["unsubscribed"]
}
```

---

## 🌍 Support multi-langue (9 langues + fallback)

### Langues supportées

- 🇫🇷 **FR** - Français
- 🇬🇧 **EN** - English (fallback)
- 🇪🇸 **ES** - Español
- 🇩🇪 **DE** - Deutsch
- 🇵🇹 **PT** - Português
- 🇷🇺 **RU** - Русский
- 🇨🇳 **ZH** - 中文
- 🇮🇳 **HI** - हिन्दी
- 🇸🇦 **AR** - العربية (RTL)

### Templates multi-langue

Chaque template peut avoir:
- **Langue** (fr, en, es, etc.)
- **Catégorie** (avocat, blogger, null = général)
- **Variables** (firstName, company, website, etc.)

**Exemple - Template avocat français:**

```json
{
  "tenant_id": 1,
  "name": "Cold outreach - Avocat FR",
  "language": "fr",
  "category": "avocat",
  "subject": "Bonjour {firstName}, développez votre cabinet avec SOS Expat",
  "body_html": "<p>Bonjour {firstName},</p>...",
  "variables": ["firstName", "company", "website"]
}
```

**Sélection automatique:**

Le système sélectionne le template selon:
1. **Langue + Catégorie** → Template avocat français
2. **Langue uniquement** → Template général français
3. **Fallback anglais** → Template général anglais

### Support RTL (Right-to-Left) pour l'arabe

Pour les templates en arabe (AR), il faut:

1. **HTML avec `dir="rtl"`:**

```html
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
  <meta charset="UTF-8">
  <style>
    body { direction: rtl; text-align: right; }
  </style>
</head>
<body>
  <p>مرحبا {firstName}،</p>
  <p>نحن نقدم خدمات لل...</p>
</body>
</html>
```

2. **Variables dans le bon ordre:**

Les variables `{firstName}`, `{company}` sont remplacées automatiquement, mais le texte autour doit être en arabe RTL.

3. **Test de rendu:**

Utiliser l'endpoint `/render` pour tester le rendu avant envoi.

---

## 📊 Pool d'IPs et warmup

### Distribution par tenant

**SOS-Expat (50 IPs):**
- **40 IPs actifs** (`45.123.10.1-40`) - weight 100
- **7 IPs en warmup** (`45.123.10.41-47`) - weight 50
- **3 IPs standby** (`45.123.10.48-50`) - weight 0

**Ulixai (50 IPs):**
- **40 IPs actifs** (`45.124.20.1-40`) - weight 100
- **7 IPs en warmup** (`45.124.20.41-47`) - weight 50
- **3 IPs standby** (`45.124.20.48-50`) - weight 0

### Warmup automatique (6 semaines)

| Semaine | Quota journalier | Safety threshold |
|---------|------------------|------------------|
| 1       | 50               | Bounce < 2%      |
| 2       | 200              | Bounce < 2%      |
| 3       | 500              | Bounce < 1.5%    |
| 4       | 1,500            | Bounce < 1.5%    |
| 5       | 5,000            | Bounce < 1%      |
| 6       | 10,000+          | Bounce < 1%      |

---

## ✅ Prochaines étapes

1. ✅ **Migration appliquée** - Tables créées
2. ✅ **Seed exécuté** - 100 IPs + 100 domaines créés
3. ⏳ **DNS configuré** - SPF, DKIM, DMARC, PTR pour 100 domaines
4. ⏳ **PowerMTA configuré** - 100 VirtualMTAs
5. ⏳ **MailWizz configuré** - 2 instances + clés API
6. ⏳ **Templates créés** - 9 langues × catégories
7. ⏳ **Intégrations** - Scraper-Pro, Backlink Engine webhooks
8. ⏳ **Celery workers** - Background jobs (validation, injection MailWizz)
9. ⏳ **Tests** - Tests unitaires + intégration

---

## 🔗 Documentation complète

- [ARCHITECTURE-ENTERPRISE.md](./ARCHITECTURE-ENTERPRISE.md) - Clean Architecture détaillée
- [ARCHITECTURE-INFRASTRUCTURE.md](./ARCHITECTURE-INFRASTRUCTURE.md) - Infrastructure 3 serveurs
- [ARCHITECTURE-MULTI-SOURCES.md](./ARCHITECTURE-MULTI-SOURCES.md) - Ingestion multi-sources

---

## 🤝 Support

Pour toute question sur l'architecture enterprise:
- Lire les docs dans `/docs`
- Vérifier les exemples dans `/src/presentation/api/v2`
- Exécuter les tests: `pytest tests/`
