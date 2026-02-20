# 🏗️ Architecture Multi-Sources - Email Engine

**Date** : 16 février 2026
**Auteur** : Claude Code
**Statut** : 🎯 PROPOSITION ARCHITECTURE

---

## 📋 TABLE DES MATIÈRES

1. [Vue d'ensemble](#1-vue-densemble)
2. [Sources de données](#2-sources-de-données)
3. [Architecture database](#3-architecture-database)
4. [Flux de données](#4-flux-de-données)
5. [Organisation code](#5-organisation-code)
6. [API endpoints](#6-api-endpoints)
7. [MailWizz multi-instance](#7-mailwizz-multi-instance)
8. [Migration plan](#8-migration-plan)

---

## 1. VUE D'ENSEMBLE

### 1.1 Objectif

**Email Engine** doit devenir le **hub central** qui :
- ✅ Reçoit des contacts de **sources multiples**
- ✅ Valide et enrichit les données
- ✅ Route vers les bonnes **instances MailWizz** (Client 1, Client 2, etc.)
- ✅ Gère des **campagnes indépendantes** par source
- ✅ Suivi granulaire par **source + campagne + contact**

### 1.2 Architecture Globale

```
┌─────────────────────────────────────────────────────────────────────┐
│                       SOURCES DE DONNÉES                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐            │
│  │ Scraper-Pro  │  │Backlink      │  │ Import CSV   │            │
│  │              │  │Engine        │  │              │            │
│  │ - Google     │  │              │  │ - Manuel     │            │
│  │ - Maps       │  │ - Prospects  │  │ - Excel      │            │
│  │ - LinkedIn   │  │ - Backlinks  │  │ - API        │            │
│  │ - Facebook   │  │              │  │              │            │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘            │
│         │                  │                  │                     │
│         └──────────────────┴──────────────────┘                    │
│                         │                                           │
│                         ↓ Webhook/API                               │
└─────────────────────────┼───────────────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────────────────┐
│                       EMAIL ENGINE (HUB)                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────────────────────────────────────────────┐      │
│  │            DATA SOURCE REGISTRY                          │      │
│  │  - Scraper-Pro (ID: scraper-pro-001)                    │      │
│  │  - Backlink Engine (ID: backlink-engine-001)            │      │
│  │  - Import CSV (ID: csv-import-001)                      │      │
│  └────────────────────┬─────────────────────────────────────┘      │
│                       │                                             │
│                       ↓                                             │
│  ┌──────────────────────────────────────────────────────────┐      │
│  │               CONTACT PIPELINE                           │      │
│  │                                                          │      │
│  │  1. Ingestion (webhook receiver)                        │      │
│  │  2. Deduplication (email hash)                          │      │
│  │  3. Validation (email SMTP check)                       │      │
│  │  4. Enrichment (categorization)                         │      │
│  │  5. Routing (Client 1 vs Client 2)                      │      │
│  └────────────────────┬─────────────────────────────────────┘      │
│                       │                                             │
│                       ↓                                             │
│  ┌──────────────────────────────────────────────────────────┐      │
│  │            CAMPAIGN MANAGER                              │      │
│  │  - Templates par source                                 │      │
│  │  - Scheduling par campagne                              │      │
│  │  - A/B testing                                          │      │
│  └────────────────────┬─────────────────────────────────────┘      │
│                       │                                             │
│                       ↓                                             │
│  ┌──────────────────────────────────────────────────────────┐      │
│  │         MAILWIZZ MULTI-INSTANCE ROUTER                   │      │
│  │  - Client 1 MailWizz (avocats, assureurs, notaires)    │      │
│  │  - Client 2 MailWizz (blogueurs, influenceurs, admins) │      │
│  │  - API sync + MySQL fallback                            │      │
│  └────────────────────┬─────────────────────────────────────┘      │
│                       │                                             │
└───────────────────────┼─────────────────────────────────────────────┘
                        │
                        ↓ API injection
┌───────────────────────┴─────────────────────────────────────────────┐
│                   MAILWIZZ INSTANCES                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────┐          ┌──────────────────┐               │
│  │ MailWizz         │          │ MailWizz         │               │
│  │ SOS-EXPAT        │          │ ULIXAI           │               │
│  │                  │          │                  │               │
│  │ Listes :         │          │ Listes :         │               │
│  │ #12 Avocats      │          │ #45 Blogueurs    │               │
│  │ #13 Assureurs    │          │ #46 Influenceurs │               │
│  │ #14 Notaires     │          │ #47 Admins FB    │               │
│  └────────┬─────────┘          └────────┬─────────┘               │
│           │                              │                         │
│           └──────────────┬───────────────┘                         │
│                          ↓                                          │
│              ┌─────────────────────┐                               │
│              │    POWERMTA         │                               │
│              │  (IPs gérées par    │                               │
│              │   Email Engine)     │                               │
│              └─────────────────────┘                               │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. SOURCES DE DONNÉES

### 2.1 Registry des Sources

Chaque source de données est enregistrée avec :

| Source | ID Unique | Type | Destination | Fréquence |
|--------|-----------|------|-------------|-----------|
| **Scraper-Pro Google** | `scraper-google-001` | scraping | Client 1 | Quotidien |
| **Scraper-Pro Maps** | `scraper-maps-001` | scraping | Client 1 | Quotidien |
| **Scraper-Pro LinkedIn** | `scraper-linkedin-001` | scraping | Client 1 | Quotidien |
| **Scraper-Pro URLs** | `scraper-urls-001` | scraping | Client 1 | Hebdo |
| **Backlink Engine** | `backlink-engine-001` | api | Client 1 | Temps réel |
| **Import CSV Manual** | `csv-manual-{timestamp}` | upload | Configurable | Ad-hoc |
| **Scraper Instagram** | `scraper-instagram-001` | scraping | Client 2 | Quotidien |
| **Scraper YouTube** | `scraper-youtube-001` | scraping | Client 2 | Quotidien |
| **Import API** | `api-{client_id}` | api | Configurable | Temps réel |

### 2.2 Metadata par Source

Chaque contact importé conserve sa **traçabilité complète** :

```json
{
  "source_id": "scraper-google-001",
  "source_type": "scraping",
  "source_config": {
    "spider": "google_search_spider",
    "query": "avocat Bangkok",
    "country": "TH",
    "language": "fr"
  },
  "imported_at": "2026-02-16T10:00:00Z",
  "import_batch_id": "batch-20260216-100000",
  "raw_data": {
    "url": "https://example.com",
    "name": "Cabinet Dupont",
    "email": "contact@example.com",
    "phone": "+66 2 123 4567",
    "social": {
      "facebook": "https://facebook.com/...",
      "linkedin": "https://linkedin.com/..."
    }
  }
}
```

---

## 3. ARCHITECTURE DATABASE

### 3.1 Nouvelles Tables Requises

#### Table `data_sources`

```sql
CREATE TABLE data_sources (
    id SERIAL PRIMARY KEY,
    source_id VARCHAR(100) UNIQUE NOT NULL,  -- 'scraper-google-001'
    source_type VARCHAR(50) NOT NULL,        -- 'scraping', 'api', 'upload', 'manual'
    name VARCHAR(255) NOT NULL,              -- 'Scraper-Pro Google Search'
    description TEXT,

    -- Configuration
    config JSONB,                            -- Configuration spécifique source
    is_active BOOLEAN DEFAULT TRUE,

    -- Routing
    default_mailwizz_instance VARCHAR(50),   -- 'client-1', 'client-2'
    default_list_mapping JSONB,              -- Mapping catégorie → list_id

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by INTEGER REFERENCES users(id),

    -- Stats (denormalized pour performance)
    total_contacts_received INTEGER DEFAULT 0,
    total_contacts_validated INTEGER DEFAULT 0,
    total_contacts_injected INTEGER DEFAULT 0,
    last_sync_at TIMESTAMP
);

CREATE INDEX idx_data_sources_source_id ON data_sources(source_id);
CREATE INDEX idx_data_sources_type ON data_sources(source_type);
CREATE INDEX idx_data_sources_mailwizz ON data_sources(default_mailwizz_instance);
```

#### Table `contacts`

```sql
CREATE TABLE contacts (
    id SERIAL PRIMARY KEY,

    -- Identification unique
    email VARCHAR(255) UNIQUE NOT NULL,
    email_hash VARCHAR(64) UNIQUE NOT NULL, -- SHA256 pour deduplication

    -- Données contact
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    company VARCHAR(255),
    phone VARCHAR(50),
    website VARCHAR(500),
    country_code CHAR(2),                    -- 'TH', 'FR', 'US', etc.
    language VARCHAR(10),                    -- 'fr', 'en', 'th', etc.

    -- Réseaux sociaux
    social_links JSONB,                      -- {facebook: '', linkedin: '', instagram: ''}

    -- Source tracking
    source_id VARCHAR(100) REFERENCES data_sources(source_id) ON DELETE SET NULL,
    import_batch_id VARCHAR(100),
    raw_data JSONB,                          -- Données brutes de la source

    -- Validation
    email_valid BOOLEAN DEFAULT NULL,        -- NULL = pas encore validé
    email_validation_result JSONB,           -- {method: 'smtp', mx_valid: true, ...}

    -- Categorization
    category VARCHAR(100),                   -- 'avocat', 'blogueur', 'assureur', etc.
    tags TEXT[],                             -- ['avocat', 'bangkok', 'expat']
    score INTEGER DEFAULT 50,                -- 0-100 (qualité lead)

    -- Routing
    mailwizz_instance VARCHAR(50),           -- 'client-1', 'client-2'
    mailwizz_list_id INTEGER,                -- ID liste MailWizz

    -- Status pipeline
    status VARCHAR(50) DEFAULT 'pending',    -- 'pending', 'validating', 'validated',
                                             -- 'invalid', 'injected', 'bounced',
                                             -- 'unsubscribed', 'blacklisted'
    status_changed_at TIMESTAMP,

    -- MailWizz sync
    mailwizz_subscriber_uid VARCHAR(50),     -- UID retourné par MailWizz
    injected_at TIMESTAMP,
    injection_result JSONB,

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- Suppression (soft delete)
    deleted_at TIMESTAMP
);

CREATE INDEX idx_contacts_email ON contacts(email);
CREATE INDEX idx_contacts_email_hash ON contacts(email_hash);
CREATE INDEX idx_contacts_source_id ON contacts(source_id);
CREATE INDEX idx_contacts_status ON contacts(status);
CREATE INDEX idx_contacts_mailwizz_instance ON contacts(mailwizz_instance);
CREATE INDEX idx_contacts_category ON contacts(category);
CREATE INDEX idx_contacts_created_at ON contacts(created_at DESC);
CREATE INDEX idx_contacts_import_batch ON contacts(import_batch_id);
```

#### Table `campaigns`

```sql
CREATE TABLE campaigns (
    id SERIAL PRIMARY KEY,

    -- Identification
    name VARCHAR(255) NOT NULL,
    description TEXT,

    -- Source liée (optionnel)
    source_id VARCHAR(100) REFERENCES data_sources(source_id),

    -- Configuration
    mailwizz_instance VARCHAR(50) NOT NULL,  -- 'client-1', 'client-2'
    mailwizz_campaign_id INTEGER,            -- ID campagne MailWizz
    mailwizz_list_id INTEGER NOT NULL,       -- ID liste MailWizz

    -- Template
    email_template_id INTEGER REFERENCES email_templates(id),
    subject_line TEXT,
    from_name VARCHAR(255),
    from_email VARCHAR(255),

    -- Scheduling
    scheduled_at TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,

    -- Segmentation
    target_category VARCHAR(100),            -- Filtre catégorie
    target_tags TEXT[],                      -- Filtre tags
    target_country_codes TEXT[],             -- Filtre pays
    max_contacts INTEGER,                    -- Limite contacts

    -- Status
    status VARCHAR(50) DEFAULT 'draft',      -- 'draft', 'scheduled', 'running',
                                             -- 'paused', 'completed', 'cancelled'

    -- Stats (denormalized)
    total_sent INTEGER DEFAULT 0,
    total_delivered INTEGER DEFAULT 0,
    total_bounced INTEGER DEFAULT 0,
    total_opened INTEGER DEFAULT 0,
    total_clicked INTEGER DEFAULT 0,
    total_unsubscribed INTEGER DEFAULT 0,

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by INTEGER REFERENCES users(id)
);

CREATE INDEX idx_campaigns_source_id ON campaigns(source_id);
CREATE INDEX idx_campaigns_mailwizz_instance ON campaigns(mailwizz_instance);
CREATE INDEX idx_campaigns_status ON campaigns(status);
CREATE INDEX idx_campaigns_scheduled_at ON campaigns(scheduled_at);
```

#### Table `email_templates`

```sql
CREATE TABLE email_templates (
    id SERIAL PRIMARY KEY,

    -- Identification
    name VARCHAR(255) NOT NULL,
    description TEXT,

    -- Source/Campagne liée (optionnel)
    source_id VARCHAR(100) REFERENCES data_sources(source_id),
    category VARCHAR(100),                   -- 'avocat', 'blogueur', etc.

    -- Contenu
    subject_line TEXT NOT NULL,
    html_content TEXT NOT NULL,
    plain_text_content TEXT,

    -- Variables disponibles
    -- {FNAME}, {LNAME}, {EMAIL}, {COMPANY}, {CUSTOM_FIELD_1}, etc.

    -- Metadata
    is_active BOOLEAN DEFAULT TRUE,
    language VARCHAR(10) DEFAULT 'fr',       -- 'fr', 'en', 'th', etc.

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by INTEGER REFERENCES users(id),

    -- Stats usage
    times_used INTEGER DEFAULT 0,
    last_used_at TIMESTAMP
);

CREATE INDEX idx_email_templates_source_id ON email_templates(source_id);
CREATE INDEX idx_email_templates_category ON email_templates(category);
CREATE INDEX idx_email_templates_language ON email_templates(language);
```

#### Table `contact_events`

```sql
CREATE TABLE contact_events (
    id SERIAL PRIMARY KEY,

    -- Relation contact
    contact_id INTEGER REFERENCES contacts(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,

    -- Relation campagne (optionnel)
    campaign_id INTEGER REFERENCES campaigns(id) ON DELETE SET NULL,

    -- Event
    event_type VARCHAR(50) NOT NULL,         -- 'validated', 'injected', 'sent', 'delivered',
                                             -- 'bounced', 'opened', 'clicked', 'unsubscribed',
                                             -- 'spam_report', 'blacklisted'
    event_data JSONB,                        -- Données additionnelles

    -- Source event (webhook MailWizz, bounce PowerMTA, etc.)
    source VARCHAR(100),                     -- 'mailwizz_webhook', 'pmta_bounce', 'manual'

    -- Metadata
    timestamp TIMESTAMP DEFAULT NOW(),
    ip_address VARCHAR(45),
    user_agent TEXT
);

CREATE INDEX idx_contact_events_contact_id ON contact_events(contact_id);
CREATE INDEX idx_contact_events_campaign_id ON contact_events(campaign_id);
CREATE INDEX idx_contact_events_event_type ON contact_events(event_type);
CREATE INDEX idx_contact_events_timestamp ON contact_events(timestamp DESC);
CREATE INDEX idx_contact_events_email ON contact_events(email);
```

#### Table `mailwizz_instances`

```sql
CREATE TABLE mailwizz_instances (
    id SERIAL PRIMARY KEY,

    -- Identification
    instance_id VARCHAR(50) UNIQUE NOT NULL, -- 'client-1', 'client-2'
    name VARCHAR(255) NOT NULL,              -- 'Client 1 MailWizz'
    description TEXT,

    -- Configuration
    api_url VARCHAR(500) NOT NULL,           -- 'https://mail.client1-domain.com/api'
    api_key VARCHAR(255) NOT NULL,           -- Clé API MailWizz

    -- Fallback MySQL (optionnel)
    mysql_enabled BOOLEAN DEFAULT FALSE,
    mysql_host VARCHAR(255),
    mysql_port INTEGER DEFAULT 3306,
    mysql_database VARCHAR(100),
    mysql_user VARCHAR(100),
    mysql_password VARCHAR(255),             -- Encrypted

    -- Default settings
    default_from_name VARCHAR(255),
    default_from_email VARCHAR(255),

    -- List mapping
    -- Mapping catégorie → list_id MailWizz
    list_mapping JSONB,                      -- {"avocat": 12, "assureur": 13, "notaire": 14}

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    last_sync_at TIMESTAMP,
    last_error TEXT,

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_mailwizz_instances_instance_id ON mailwizz_instances(instance_id);
```

### 3.2 Relations Clés

```
data_sources (1) ──→ (N) contacts
                 ──→ (N) campaigns
                 ──→ (N) email_templates

contacts (1) ──→ (N) contact_events

campaigns (1) ──→ (N) contact_events
          (1) ──→ (1) email_templates

mailwizz_instances (1) ──→ (N) contacts (routing)
                   (1) ──→ (N) campaigns
```

---

## 4. FLUX DE DONNÉES

### 4.1 Ingestion Contact (Webhook/API)

```
1. POST /api/v1/contacts/ingest
   {
     "source_id": "scraper-google-001",
     "contacts": [
       {
         "email": "contact@example.com",
         "first_name": "Jean",
         "last_name": "Dupont",
         "company": "Cabinet Dupont",
         "phone": "+66 2 123 4567",
         "website": "https://example.com",
         "country_code": "TH",
         "language": "fr",
         "category": "avocat",
         "tags": ["avocat", "bangkok", "expat"],
         "raw_data": {...}
       }
     ]
   }

2. Email Engine Process:
   ├─ Validation source_id (existe?)
   ├─ Deduplication (email_hash SHA256)
   ├─ Insert contact (status='pending')
   ├─ Event 'ingested' créé
   └─ Return batch_id

3. Background Job (Cron 1h):
   ├─ SELECT contacts WHERE status='pending' LIMIT 1000
   ├─ Validation email (SMTP check)
   │  ├─ Valid → status='validated'
   │  └─ Invalid → status='invalid'
   ├─ Enrichment (catégorisation si manquante)
   └─ Routing (mailwizz_instance, mailwizz_list_id)

4. Injection MailWizz (Cron 1h):
   ├─ SELECT contacts WHERE status='validated' AND injected_at IS NULL
   ├─ Group by mailwizz_instance
   ├─ Pour chaque instance:
   │  ├─ Batch API call MailWizz
   │  ├─ Update mailwizz_subscriber_uid
   │  ├─ status='injected'
   │  └─ Event 'injected' créé
   └─ Alert Telegram si erreurs
```

### 4.2 Création Campagne

```
1. POST /api/v1/campaigns
   {
     "name": "Campagne Avocats Bangkok",
     "source_id": "scraper-google-001",  // Optionnel
     "mailwizz_instance": "client-1",
     "mailwizz_list_id": 12,
     "email_template_id": 5,
     "subject_line": "Partenariat Client 1",
     "from_name": "William - Client 1",
     "from_email": "contact@client1-domain.com",
     "target_category": "avocat",
     "target_tags": ["bangkok", "expat"],
     "target_country_codes": ["TH"],
     "max_contacts": 500,
     "scheduled_at": "2026-02-20T10:00:00Z"
   }

2. Email Engine Process:
   ├─ Validation template exists
   ├─ Validation MailWizz instance exists
   ├─ Count target contacts
   ├─ Create campaign (status='draft')
   └─ Return campaign_id

3. Scheduler (Cron 5min):
   ├─ SELECT campaigns WHERE status='scheduled' AND scheduled_at <= NOW()
   ├─ Pour chaque campagne:
   │  ├─ Create MailWizz campaign via API
   │  ├─ Update mailwizz_campaign_id
   │  ├─ status='running'
   │  └─ Alert Telegram "Campagne lancée"
   └─ Log audit
```

### 4.3 Webhooks MailWizz

```
POST /api/v1/webhooks/mailwizz/{event}
{
  "subscriber_uid": "ab12cd34",
  "email": "contact@example.com",
  "campaign_uid": "cd34ef56",
  "event_type": "email_opened",
  "timestamp": "2026-02-20T12:34:56Z",
  "ip_address": "1.2.3.4",
  "user_agent": "Mozilla/5.0 ..."
}

Process:
├─ Find contact by mailwizz_subscriber_uid
├─ Find campaign by mailwizz_campaign_uid
├─ Create contact_event
├─ Update campaign stats (denormalized)
└─ Update contact stats if needed
```

---

## 5. ORGANISATION CODE

### 5.1 Structure Modifiée

```
email-engine/
├── app/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── ips.py                      # Existant
│   │   │   ├── domains.py                  # Existant
│   │   │   ├── warmup.py                   # Existant
│   │   │   ├── blacklists.py               # Existant
│   │   │   ├── webhooks.py                 # Existant (PMTA bounces)
│   │   │   │
│   │   │   ├── data_sources.py             # NOUVEAU - Gestion sources
│   │   │   ├── contacts.py                 # NOUVEAU - Ingestion + CRUD contacts
│   │   │   ├── campaigns.py                # NOUVEAU - Gestion campagnes
│   │   │   ├── email_templates.py          # NOUVEAU - Templates emails
│   │   │   ├── mailwizz.py                 # NOUVEAU - Config instances MailWizz
│   │   │   └── webhooks_mailwizz.py        # NOUVEAU - Webhooks MailWizz
│   │   │
│   │   └── dependencies.py                 # Existant (auth JWT)
│   │
│   ├── services/
│   │   ├── blacklist_checker.py            # Existant
│   │   ├── dns_validator.py                # Existant
│   │   ├── pmta_manager.py                 # Existant
│   │   ├── mailwizz_client.py              # Existant (à étendre)
│   │   ├── telegram_alerts.py              # Existant
│   │   │
│   │   ├── contact_validator.py            # NOUVEAU - Validation email SMTP
│   │   ├── contact_enricher.py             # NOUVEAU - Enrichissement data
│   │   ├── contact_router.py               # NOUVEAU - Routing vers MailWizz
│   │   ├── mailwizz_multi_client.py        # NOUVEAU - Client multi-instance
│   │   ├── campaign_manager.py             # NOUVEAU - Gestion campagnes
│   │   └── deduplicator.py                 # NOUVEAU - Dédoublonnage contacts
│   │
│   ├── scheduler/
│   │   ├── jobs.py                         # Existant (warmup, blacklist, etc.)
│   │   │
│   │   ├── contact_validation_job.py       # NOUVEAU - Validation batch contacts
│   │   ├── contact_injection_job.py        # NOUVEAU - Injection MailWizz batch
│   │   ├── campaign_scheduler_job.py       # NOUVEAU - Lancement campagnes
│   │   └── stats_aggregation_job.py        # NOUVEAU - Aggregation stats
│   │
│   ├── models.py                           # Existant + NOUVEAUX MODÈLES
│   ├── schemas.py                          # NOUVEAU - Pydantic schemas
│   ├── enums.py                            # Existant + NOUVEAUX ENUMS
│   ├── config.py                           # Existant (settings)
│   ├── database.py                         # Existant (SQLAlchemy)
│   └── main.py                             # Existant (FastAPI app)
│
├── alembic/
│   └── versions/
│       └── 2026_02_16_add_multi_sources.py # NOUVELLE MIGRATION
│
├── tests/
│   ├── test_auth.py                        # Existant
│   ├── test_ips.py                         # Existant
│   │
│   ├── test_contacts.py                    # NOUVEAU
│   ├── test_campaigns.py                   # NOUVEAU
│   ├── test_mailwizz_multi.py              # NOUVEAU
│   └── test_webhooks_mailwizz.py           # NOUVEAU
│
├── scripts/
│   ├── manage-users.py                     # Existant
│   │
│   ├── import-csv.py                       # NOUVEAU - Import CSV manuel
│   ├── backfill-contacts.py                # NOUVEAU - Migration contacts existants
│   └── test-mailwizz-connection.py         # NOUVEAU - Test connexions MailWizz
│
└── docs/
    ├── API-SOURCES.md                      # NOUVEAU - Doc API sources
    ├── API-CONTACTS.md                     # NOUVEAU - Doc API contacts
    ├── API-CAMPAIGNS.md                    # NOUVEAU - Doc API campagnes
    └── MAILWIZZ-SETUP.md                   # NOUVEAU - Setup multi-instance
```

### 5.2 Nouveaux Enums

```python
# app/enums.py (additions)

class ContactStatus(str, Enum):
    PENDING = "pending"
    VALIDATING = "validating"
    VALIDATED = "validated"
    INVALID = "invalid"
    INJECTED = "injected"
    BOUNCED = "bounced"
    UNSUBSCRIBED = "unsubscribed"
    BLACKLISTED = "blacklisted"

class SourceType(str, Enum):
    SCRAPING = "scraping"
    API = "api"
    UPLOAD = "upload"
    MANUAL = "manual"

class CampaignStatus(str, Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class ContactEventType(str, Enum):
    INGESTED = "ingested"
    VALIDATED = "validated"
    INVALID = "invalid"
    INJECTED = "injected"
    SENT = "sent"
    DELIVERED = "delivered"
    BOUNCED = "bounced"
    OPENED = "opened"
    CLICKED = "clicked"
    UNSUBSCRIBED = "unsubscribed"
    SPAM_REPORT = "spam_report"
    BLACKLISTED = "blacklisted"

class MailWizzInstance(str, Enum):
    CLIENT1 = "client-1"
    CLIENT2 = "client-2"
```

---

## 6. API ENDPOINTS

### 6.1 Data Sources Management

```python
# GET /api/v1/data-sources
# Liste toutes les sources configurées

# POST /api/v1/data-sources
# Crée une nouvelle source
{
  "source_id": "scraper-google-001",
  "source_type": "scraping",
  "name": "Scraper-Pro Google Search",
  "description": "Scraping Google pour avocats internationaux",
  "config": {
    "spider": "google_search_spider",
    "query_template": "avocat {country}",
    "max_results": 100
  },
  "default_mailwizz_instance": "client-1",
  "default_list_mapping": {
    "avocat": 12,
    "assureur": 13,
    "notaire": 14
  }
}

# GET /api/v1/data-sources/{source_id}
# Détails source + stats

# PATCH /api/v1/data-sources/{source_id}
# Mise à jour config source

# DELETE /api/v1/data-sources/{source_id}
# Soft delete source (is_active=false)
```

### 6.2 Contacts Ingestion & Management

```python
# POST /api/v1/contacts/ingest
# Ingestion batch contacts (webhook externe)
{
  "source_id": "scraper-google-001",
  "contacts": [
    {
      "email": "contact@example.com",
      "first_name": "Jean",
      "last_name": "Dupont",
      "company": "Cabinet Dupont",
      "phone": "+66 2 123 4567",
      "website": "https://example.com",
      "country_code": "TH",
      "language": "fr",
      "category": "avocat",
      "tags": ["avocat", "bangkok", "expat"],
      "raw_data": {}
    }
  ]
}
# Returns: { "batch_id": "...", "accepted": 95, "duplicates": 5 }

# GET /api/v1/contacts
# Liste contacts avec filtres
# ?source_id=scraper-google-001
# &status=validated
# &category=avocat
# &mailwizz_instance=client-1
# &page=1&limit=50

# GET /api/v1/contacts/{contact_id}
# Détails contact + events

# PATCH /api/v1/contacts/{contact_id}
# Mise à jour contact manuel

# DELETE /api/v1/contacts/{contact_id}
# Soft delete contact

# POST /api/v1/contacts/{contact_id}/validate
# Force validation email immédiate

# POST /api/v1/contacts/{contact_id}/inject
# Force injection MailWizz immédiate
```

### 6.3 Campaigns Management

```python
# POST /api/v1/campaigns
# Création campagne
{
  "name": "Campagne Avocats Bangkok",
  "description": "Partenariat avocats expatriés",
  "source_id": "scraper-google-001",
  "mailwizz_instance": "client-1",
  "mailwizz_list_id": 12,
  "email_template_id": 5,
  "subject_line": "Partenariat Client 1",
  "from_name": "William - Client 1",
  "from_email": "contact@client1-domain.com",
  "target_category": "avocat",
  "target_tags": ["bangkok", "expat"],
  "target_country_codes": ["TH"],
  "max_contacts": 500,
  "scheduled_at": "2026-02-20T10:00:00Z"
}

# GET /api/v1/campaigns
# Liste campagnes avec filtres

# GET /api/v1/campaigns/{campaign_id}
# Détails campagne + stats temps réel

# PATCH /api/v1/campaigns/{campaign_id}
# Mise à jour campagne

# POST /api/v1/campaigns/{campaign_id}/launch
# Lancement immédiat (bypass scheduled_at)

# POST /api/v1/campaigns/{campaign_id}/pause
# Pause campagne en cours

# POST /api/v1/campaigns/{campaign_id}/resume
# Reprise campagne pausée

# DELETE /api/v1/campaigns/{campaign_id}
# Annulation campagne
```

### 6.4 Email Templates

```python
# POST /api/v1/email-templates
# Création template
{
  "name": "Template Avocats FR",
  "description": "Email partenariat avocats francophones",
  "source_id": "scraper-google-001",
  "category": "avocat",
  "subject_line": "Partenariat Client 1 - {COMPANY}",
  "html_content": "<html>...</html>",
  "plain_text_content": "Bonjour {FNAME}...",
  "language": "fr"
}

# GET /api/v1/email-templates
# Liste templates

# GET /api/v1/email-templates/{template_id}
# Détails template

# PATCH /api/v1/email-templates/{template_id}
# Mise à jour template

# DELETE /api/v1/email-templates/{template_id}
# Suppression template
```

### 6.5 MailWizz Instances

```python
# POST /api/v1/mailwizz-instances
# Configuration nouvelle instance
{
  "instance_id": "client-1",
  "name": "Client 1 MailWizz",
  "api_url": "https://mail.client1-domain.com/api",
  "api_key": "YOUR_API_KEY",
  "mysql_enabled": true,
  "mysql_host": "localhost",
  "mysql_database": "mailwizz",
  "mysql_user": "mailwizz",
  "mysql_password": "encrypted_password",
  "default_from_name": "Client 1",
  "default_from_email": "contact@client1-domain.com",
  "list_mapping": {
    "avocat": 12,
    "assureur": 13,
    "notaire": 14
  }
}

# GET /api/v1/mailwizz-instances
# Liste instances

# GET /api/v1/mailwizz-instances/{instance_id}
# Détails instance

# POST /api/v1/mailwizz-instances/{instance_id}/test
# Test connexion API + MySQL

# PATCH /api/v1/mailwizz-instances/{instance_id}
# Mise à jour config

# DELETE /api/v1/mailwizz-instances/{instance_id}
# Désactivation instance
```

### 6.6 Webhooks MailWizz

```python
# POST /api/v1/webhooks/mailwizz/email-sent
# POST /api/v1/webhooks/mailwizz/email-delivered
# POST /api/v1/webhooks/mailwizz/email-opened
# POST /api/v1/webhooks/mailwizz/email-clicked
# POST /api/v1/webhooks/mailwizz/email-bounced
# POST /api/v1/webhooks/mailwizz/email-unsubscribed
# POST /api/v1/webhooks/mailwizz/email-spam-report

# Body example:
{
  "subscriber_uid": "ab12cd34",
  "email": "contact@example.com",
  "campaign_uid": "cd34ef56",
  "timestamp": "2026-02-20T12:34:56Z",
  "ip_address": "1.2.3.4",
  "user_agent": "Mozilla/5.0 ...",
  "event_data": {}
}
```

---

## 7. MAILWIZZ MULTI-INSTANCE

### 7.1 Configuration

```python
# app/services/mailwizz_multi_client.py

class MailWizzMultiClient:
    """Client pour gérer plusieurs instances MailWizz."""

    def __init__(self, db: Session):
        self.db = db
        self.instances: Dict[str, MailWizzInstanceClient] = {}
        self._load_instances()

    def _load_instances(self):
        """Charge toutes les instances actives depuis DB."""
        instances = self.db.query(MailWizzInstance).filter(
            MailWizzInstance.is_active == True
        ).all()

        for instance in instances:
            self.instances[instance.instance_id] = MailWizzInstanceClient(
                api_url=instance.api_url,
                api_key=instance.api_key,
                mysql_config={
                    "host": instance.mysql_host,
                    "database": instance.mysql_database,
                    "user": instance.mysql_user,
                    "password": decrypt(instance.mysql_password)
                } if instance.mysql_enabled else None
            )

    def get_client(self, instance_id: str) -> MailWizzInstanceClient:
        """Retourne client pour instance spécifique."""
        if instance_id not in self.instances:
            raise ValueError(f"MailWizz instance '{instance_id}' not found")
        return self.instances[instance_id]

    async def inject_contact(
        self,
        instance_id: str,
        list_id: int,
        contact: Contact
    ) -> Dict[str, Any]:
        """Injecte contact dans instance MailWizz spécifique."""
        client = self.get_client(instance_id)

        try:
            # Tentative API
            result = await client.add_subscriber(list_id, {
                "EMAIL": contact.email,
                "FNAME": contact.first_name,
                "LNAME": contact.last_name,
                "COMPANY": contact.company,
                "PHONE": contact.phone,
                # Custom fields
                "SOURCE": contact.source_id,
                "CATEGORY": contact.category,
                "TAGS": ",".join(contact.tags or [])
            })

            return {
                "method": "api",
                "subscriber_uid": result["subscriber_uid"],
                "status": "success"
            }

        except Exception as api_error:
            # Fallback MySQL direct
            if client.mysql_config:
                try:
                    result = await client.add_subscriber_mysql(list_id, contact)
                    return {
                        "method": "mysql",
                        "subscriber_id": result["subscriber_id"],
                        "status": "success"
                    }
                except Exception as mysql_error:
                    raise Exception(f"API + MySQL failed: {api_error}, {mysql_error}")
            else:
                raise api_error
```

### 7.2 Routing Automatique

```python
# app/services/contact_router.py

class ContactRouter:
    """Route les contacts vers la bonne instance MailWizz."""

    def __init__(self, db: Session):
        self.db = db

    def route_contact(self, contact: Contact) -> Tuple[str, int]:
        """
        Détermine instance MailWizz + list_id pour contact.

        Returns:
            (instance_id, list_id)
        """
        # 1. Vérifier si source a routing par défaut
        source = self.db.query(DataSource).filter(
            DataSource.source_id == contact.source_id
        ).first()

        if source and source.default_mailwizz_instance:
            instance_id = source.default_mailwizz_instance

            # Mapper catégorie → list_id
            if contact.category and source.default_list_mapping:
                list_id = source.default_list_mapping.get(contact.category)
                if list_id:
                    return (instance_id, list_id)

        # 2. Règles business custom
        if contact.category in ["avocat", "assureur", "notaire"]:
            instance_id = "client-1"
            list_mapping = {
                "avocat": 12,
                "assureur": 13,
                "notaire": 14
            }
            list_id = list_mapping[contact.category]
            return (instance_id, list_id)

        elif contact.category in ["blogueur", "influenceur", "admin_facebook"]:
            instance_id = "client-2"
            list_mapping = {
                "blogueur": 45,
                "influenceur": 46,
                "admin_facebook": 47
            }
            list_id = list_mapping[contact.category]
            return (instance_id, list_id)

        # 3. Fallback : lever erreur
        raise ValueError(f"Cannot route contact {contact.id}: no routing rule found")
```

---

## 8. MIGRATION PLAN

### 8.1 Phase 1 : Database & Models (Semaine 1)

**Tâches** :
- ✅ Créer migration Alembic avec 6 nouvelles tables
- ✅ Ajouter nouveaux models SQLAlchemy
- ✅ Ajouter nouveaux enums
- ✅ Créer schemas Pydantic (validation API)
- ✅ Tests unitaires models

**Fichiers** :
- `alembic/versions/2026_02_16_add_multi_sources.py`
- `app/models.py` (ajouts)
- `app/enums.py` (ajouts)
- `app/schemas.py` (nouveau)

### 8.2 Phase 2 : Services Core (Semaine 2)

**Tâches** :
- ✅ `contact_validator.py` (validation SMTP)
- ✅ `contact_enricher.py` (catégorisation)
- ✅ `contact_router.py` (routing MailWizz)
- ✅ `mailwizz_multi_client.py` (multi-instance)
- ✅ `deduplicator.py` (SHA256 hash)
- ✅ Tests unitaires services

**Fichiers** :
- `app/services/contact_validator.py`
- `app/services/contact_enricher.py`
- `app/services/contact_router.py`
- `app/services/mailwizz_multi_client.py`
- `app/services/deduplicator.py`

### 8.3 Phase 3 : API Endpoints (Semaine 3)

**Tâches** :
- ✅ Routes data sources (CRUD)
- ✅ Routes contacts (ingestion + CRUD)
- ✅ Routes campaigns (CRUD + launch/pause)
- ✅ Routes email templates (CRUD)
- ✅ Routes MailWizz instances (config)
- ✅ Webhooks MailWizz (events)
- ✅ Tests intégration API

**Fichiers** :
- `app/api/routes/data_sources.py`
- `app/api/routes/contacts.py`
- `app/api/routes/campaigns.py`
- `app/api/routes/email_templates.py`
- `app/api/routes/mailwizz.py`
- `app/api/routes/webhooks_mailwizz.py`

### 8.4 Phase 4 : Scheduled Jobs (Semaine 4)

**Tâches** :
- ✅ Job validation contacts (cron 1h)
- ✅ Job injection MailWizz (cron 1h)
- ✅ Job lancement campagnes (cron 5min)
- ✅ Job aggregation stats (cron 1h)
- ✅ Tests jobs

**Fichiers** :
- `app/scheduler/contact_validation_job.py`
- `app/scheduler/contact_injection_job.py`
- `app/scheduler/campaign_scheduler_job.py`
- `app/scheduler/stats_aggregation_job.py`

### 8.5 Phase 5 : Scripts & Tools (Semaine 5)

**Tâches** :
- ✅ Script import CSV
- ✅ Script backfill contacts existants
- ✅ Script test connexions MailWizz
- ✅ Documentation API complète
- ✅ Tests end-to-end

**Fichiers** :
- `scripts/import-csv.py`
- `scripts/backfill-contacts.py`
- `scripts/test-mailwizz-connection.py`
- `docs/API-*.md`

### 8.6 Phase 6 : Production Deployment (Semaine 6)

**Tâches** :
- ✅ Backup database production
- ✅ Run migration Alembic en prod
- ✅ Configuration instances MailWizz (Client 1, Client 2)
- ✅ Configuration sources initiales
- ✅ Tests smoke production
- ✅ Monitoring Grafana (nouvelles métriques)
- ✅ Documentation opérationnelle

---

## 9. PROCHAINES ÉTAPES

### 🎯 Action Immédiate

**Tu veux que je** :

1. ✅ **Créer la migration Alembic** avec les 6 nouvelles tables ?
2. ✅ **Ajouter les nouveaux models** à `app/models.py` ?
3. ✅ **Créer les schemas Pydantic** pour validation API ?
4. ✅ **Implémenter les premiers services** (validator, router) ?
5. ✅ **Créer les routes API** pour data sources + contacts ?

**OU** tu veux d'abord :
- 🤔 Discuter de l'architecture proposée
- 🔧 Ajuster certains aspects
- 📊 Voir un exemple concret de flux

---

**Dis-moi ce que tu veux faire en premier et je lance l'implémentation !** 🚀
