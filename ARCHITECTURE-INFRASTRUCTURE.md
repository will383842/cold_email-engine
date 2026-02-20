# 🏗️ ARCHITECTURE INFRASTRUCTURE - Multi-Serveurs & Pool IPs Rotatif

**Date** : 16 février 2026
**Statut** : 🎯 **INFRASTRUCTURE PRODUCTION SCALABLE**

---

## 📋 TABLE DES MATIÈRES

1. [Vue d'ensemble Infrastructure](#1-vue-densemble-infrastructure)
2. [Serveurs Dédiés](#2-serveurs-dédiés)
3. [Pool IPs Rotatif (Anti-Blacklist)](#3-pool-ips-rotatif-anti-blacklist)
4. [Domaines Multiples Rotatifs](#4-domaines-multiples-rotatifs)
5. [Isolation Multi-Tenant](#5-isolation-multi-tenant)
6. [Warmup IPs Automatisé](#6-warmup-ips-automatisé)
7. [Rotation Intelligente](#7-rotation-intelligente)
8. [Monitoring & Failover](#8-monitoring--failover)
9. [DNS Configuration](#9-dns-configuration)
10. [Déploiement Production](#10-déploiement-production)

---

## 1. VUE D'ENSEMBLE INFRASTRUCTURE

### 1.1 Architecture 3 Serveurs

```
┌──────────────────────────────────────────────────────────────────────┐
│                         INTERNET                                     │
└────────────────────┬─────────────────────────────────────────────────┘
                     │
                     ↓
┌────────────────────────────────────────────────────────────────────────┐
│                    SERVEUR 1: EMAIL ENGINE API                         │
│                    VPS: 4 vCPU, 8GB RAM, 100GB SSD                     │
│                    IP: 89.167.1.10 (IP publique fixe)                  │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  ┌─────────────────────────────────────────────────────────────┐      │
│  │  FastAPI (Email Engine)                                     │      │
│  │  - API REST (v1 + v2)                                       │      │
│  │  - Use Cases (contacts, campaigns, templates)              │      │
│  │  - Business Logic                                           │      │
│  └─────────────────────────────────────────────────────────────┘      │
│                              ↓ ↑                                       │
│  ┌─────────────────────────────────────────────────────────────┐      │
│  │  PostgreSQL 15                                              │      │
│  │  - Contacts, Campaigns, Templates, Tags                     │      │
│  │  - IPs, Domains, Warmup Plans                               │      │
│  │  - Contact Events (tracking)                                │      │
│  └─────────────────────────────────────────────────────────────┘      │
│                              ↓ ↑                                       │
│  ┌─────────────────────────────────────────────────────────────┐      │
│  │  Redis Cluster (3 nodes)                                    │      │
│  │  - Cache (contacts, templates, stats)                       │      │
│  │  - Rate limiting                                            │      │
│  │  - Session storage                                          │      │
│  │  - Message Queue (pub/sub)                                  │      │
│  └─────────────────────────────────────────────────────────────┘      │
│                              ↓ ↑                                       │
│  ┌─────────────────────────────────────────────────────────────┐      │
│  │  Celery Workers (auto-scaling)                              │      │
│  │  - Contact validation (SMTP check)                          │      │
│  │  - Contact enrichment                                       │      │
│  │  - MailWizz injection (batch)                               │      │
│  │  - Campaign stats aggregation                               │      │
│  └─────────────────────────────────────────────────────────────┘      │
│                                                                        │
└──────────────────┬─────────────────────────────────────┬───────────────┘
                   │                                     │
                   │ API REST                            │ API REST
                   │ (HTTPS)                             │ (HTTPS)
                   ↓                                     ↓
┌────────────────────────────────────────┐  ┌───────────────────────────────────┐
│  SERVEUR 2A: MAILWIZZ SOS-EXPAT        │  │  SERVEUR 2B: MAILWIZZ ULIXAI      │
│  VPS: 4 vCPU, 8GB RAM, 200GB SSD       │  │  VPS: 4 vCPU, 8GB RAM, 200GB SSD  │
│  IP: 89.167.2.10                       │  │  IP: 89.167.3.10                  │
├────────────────────────────────────────┤  ├───────────────────────────────────┤
│                                        │  │                                   │
│  MailWizz Client 1                     │  │  MailWizz Client 2                │
│  - Domain: mailwizz-sos.com            │  │  - Domain: mailwizz-client2.com   │
│  - API REST                            │  │  - API REST                       │
│  - MySQL Database (subscribers)        │  │  - MySQL Database (subscribers)   │
│  - Lists Management                    │  │  - Lists Management               │
│                                        │  │                                   │
│  Listes:                               │  │  Listes:                          │
│  - #12: Avocats                        │  │  - #20: Blogueurs                 │
│  - #13: Assureurs                      │  │  - #21: Influenceurs              │
│  - #14: Notaires                       │  │  - #22: Admins groupes            │
│  - #15: Expat Aidants                  │  │  - #30: Clients                   │
│                                        │  │                                   │
└──────────────┬─────────────────────────┘  └────────────┬──────────────────────┘
               │                                         │
               │ SMTP (envoi emails)                     │ SMTP (envoi emails)
               │                                         │
               └─────────────────┬───────────────────────┘
                                 ↓
┌────────────────────────────────────────────────────────────────────────┐
│            SERVEUR 3: POWERMTA + POOL IPs ROTATIF                      │
│            VDS: 8 vCPU, 16GB RAM, 500GB SSD                            │
│            IP Management: 100.1.1.1 (admin)                            │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────┐     │
│  │              POWERMTA (SMTP MTA)                             │     │
│  │  - Config dynamique (géré par Email Engine)                 │     │
│  │  - VirtualMTA (rotation IPs)                                │     │
│  │  - Queue management                                         │     │
│  │  - Bounce handling                                          │     │
│  └──────────────────────────────────────────────────────────────┘     │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────┐     │
│  │         POOL IPs SOS-EXPAT (50 IPs dédiées)                 │     │
│  │                                                              │     │
│  │  Active (warming/active):                                   │     │
│  │  - 45.123.10.1  → sos-mail-1.com    [ACTIVE - Week 6]      │     │
│  │  - 45.123.10.2  → sos-mail-2.com    [ACTIVE - Week 6]      │     │
│  │  - 45.123.10.3  → sos-mail-3.com    [WARMING - Week 3]     │     │
│  │  - 45.123.10.4  → sos-mail-4.com    [WARMING - Week 2]     │     │
│  │  - ... (46 autres IPs)                                      │     │
│  │                                                              │     │
│  │  Standby (remplacement):                                    │     │
│  │  - 45.123.10.48 → sos-mail-48.com   [STANDBY]              │     │
│  │  - 45.123.10.49 → sos-mail-49.com   [STANDBY]              │     │
│  │  - 45.123.10.50 → sos-mail-50.com   [STANDBY]              │     │
│  └──────────────────────────────────────────────────────────────┘     │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────┐     │
│  │         POOL IPs ULIXAI (50 IPs dédiées)                    │     │
│  │                                                              │     │
│  │  Active (warming/active):                                   │     │
│  │  - 45.124.20.1  → client2-mail-1.com  [ACTIVE - Week 6]     │     │
│  │  - 45.124.20.2  → client2-mail-2.com  [ACTIVE - Week 6]     │     │
│  │  - 45.124.20.3  → client2-mail-3.com  [WARMING - Week 4]    │     │
│  │  - ... (47 autres IPs)                                      │     │
│  │                                                              │     │
│  │  Standby (remplacement):                                    │     │
│  │  - 45.124.20.50 → client2-mail-50.com [STANDBY]             │     │
│  └──────────────────────────────────────────────────────────────┘     │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. SERVEURS DÉDIÉS

### 2.1 Serveur 1: Email Engine API

**Rôle** : Hub central orchestration

**Specs** :
- VPS: 4 vCPU, 8GB RAM, 100GB SSD
- OS: Ubuntu 22.04 LTS
- IP: 89.167.1.10 (publique fixe)
- Domain: api.email-engine.com

**Stack** :
```
- FastAPI (Email Engine API)
- PostgreSQL 15 (database principale)
- Redis Cluster (cache + queue)
- Celery Workers (background jobs)
- Nginx (reverse proxy + SSL)
- Prometheus + Grafana (monitoring)
```

**Connexions sortantes** :
- → MailWizz Client 1 (89.167.2.10:443) - API REST
- → MailWizz Client 2 (89.167.3.10:443) - API REST
- → PowerMTA (100.1.1.1:25 + API) - SMTP + API
- → Scraper-Pro (webhook receiver)
- → Backlink Engine (webhook receiver)

**Firewall** :
```bash
# Entrantes
ALLOW 443/tcp from anywhere  # HTTPS API
ALLOW 22/tcp from admin_ip    # SSH admin

# Sortantes
ALLOW 443/tcp to 89.167.2.10  # MailWizz Client 1
ALLOW 443/tcp to 89.167.3.10  # MailWizz Client 2
ALLOW 25/tcp to 100.1.1.1     # PowerMTA SMTP
ALLOW 443/tcp to 100.1.1.1    # PowerMTA API
```

### 2.2 Serveur 2A: MailWizz Client 1

**Rôle** : Plateforme email marketing Client 1

**Specs** :
- VPS: 4 vCPU, 8GB RAM, 200GB SSD
- OS: Ubuntu 22.04 LTS
- IP: 89.167.2.10
- Domain: mailwizz-sos.com

**Stack** :
```
- MailWizz (PHP 8.1 + MySQL 8.0)
- Nginx + PHP-FPM
- MySQL 8.0 (subscribers database)
- SSL/TLS (Let's Encrypt)
```

**Configuration MailWizz** :
```php
// config/main.php
'components' => [
    'deliveryServers' => [
        'powerMTA' => [
            'host' => '100.1.1.1',
            'port' => 25,
            'protocol' => 'smtp',
            'username' => '',  // Pas d'auth (IP whitelisted)
            'password' => '',
        ]
    ]
]
```

**Listes MailWizz Client 1** :
```
#12 - Avocats Internationaux
#13 - Assureurs Expat
#14 - Notaires
#15 - Expat Aidants
#16 - Blogueurs (SOS)
#17 - Influenceurs (SOS)
#18 - Chatters
#19 - Admins Groupes
#30 - Clients (Vacanciers, Expats, Digital Nomades)
```

### 2.3 Serveur 2B: MailWizz Client 2

**Rôle** : Plateforme email marketing Client 2

**Specs** : Identique à 2A
- VPS: 4 vCPU, 8GB RAM, 200GB SSD
- IP: 89.167.3.10
- Domain: mailwizz-client2.com

**Listes MailWizz Client 2** :
```
#20 - Blogueurs Voyage
#21 - Influenceurs Instagram/YouTube
#22 - Admins Groupes Facebook
#30 - Clients Client 2
```

### 2.4 Serveur 3: PowerMTA + Pool IPs

**Rôle** : MTA (Mail Transfer Agent) + Pool IPs rotatif

**Specs** :
- VDS: 8 vCPU, 16GB RAM, 500GB SSD
- OS: CentOS 7 / RHEL 8 (PowerMTA requirement)
- IP Admin: 100.1.1.1
- IPs Pool: 100 IPs dédiées (50 Client 1 + 50 Client 2)

**Stack** :
```
- PowerMTA 5.0
- Email Engine Agent (sync config)
- Monitoring (blacklist checker)
```

**Provider IPs** :
- Hetzner / OVH / Contabo
- /24 subnet dédiés (256 IPs disponibles)
- IPs clean (jamais utilisées pour spam)

---

## 3. POOL IPs ROTATIF (ANTI-BLACKLIST)

### 3.1 Stratégie Pool IPs

**Pourquoi pool rotatif ?**
- ✅ Éviter blacklist (rotation si détection)
- ✅ Diluer volume envoi (pas de saturation)
- ✅ Warmup progressif (6 semaines)
- ✅ Haute disponibilité (standby IPs)

**Pool Client 1** :

| Pool | Nombre | Status | Usage |
|------|--------|--------|-------|
| **Active** | 40 IPs | ACTIVE (Week 6 warmup) | Envoi quotidien production |
| **Warming** | 7 IPs | WARMING (Week 1-5) | Warmup progressif |
| **Standby** | 3 IPs | STANDBY (ready) | Remplacement si blacklist |
| **Total** | **50 IPs** | - | - |

**Pool Client 2** : Identique (50 IPs)

### 3.2 Configuration Database (table `ips`)

```sql
-- Table existante (déjà dans email-engine)
CREATE TABLE ips (
    id SERIAL PRIMARY KEY,

    -- Identity
    address VARCHAR(45) UNIQUE NOT NULL,     -- '45.123.10.1'
    hostname VARCHAR(255) NOT NULL,          -- 'sos-mail-1.com'

    -- Tenant (NOUVEAU - isolation)
    tenant VARCHAR(50) NOT NULL,             -- 'client-1', 'client-2'

    -- Purpose
    purpose VARCHAR(20) DEFAULT 'marketing', -- 'marketing', 'transactional'

    -- Status (état IP)
    status VARCHAR(20) DEFAULT 'standby',    -- 'standby', 'warming', 'active',
                                             -- 'quarantine', 'retiring', 'resting'

    -- PowerMTA config
    vmta_name VARCHAR(100),                  -- 'sos-vmta-1'
    pool_name VARCHAR(100),                  -- 'sos-pool'
    weight INTEGER DEFAULT 100,              -- Poids rotation (0-100)

    -- MailWizz sync
    mailwizz_server_id INTEGER,             -- ID delivery server MailWizz

    -- Blacklist protection
    quarantine_until TIMESTAMP,
    blacklisted_on TEXT DEFAULT '[]',       -- JSON array blacklists

    -- Warmup
    warmup_phase VARCHAR(20),               -- 'week_1', 'week_2', ..., 'week_6'
    warmup_started_at TIMESTAMP,

    -- Metadata
    status_changed_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT uq_ip_tenant UNIQUE (address, tenant)
);

CREATE INDEX idx_ips_tenant ON ips(tenant);
CREATE INDEX idx_ips_status ON ips(status);
CREATE INDEX idx_ips_tenant_status ON ips(tenant, status);
CREATE INDEX idx_ips_pool ON ips(pool_name);
```

### 3.3 Seed Data Pool IPs

```sql
-- Pool Client 1 (50 IPs)
INSERT INTO ips (address, hostname, tenant, purpose, pool_name, vmta_name, status, weight) VALUES
-- Active (40 IPs)
('45.123.10.1', 'sos-mail-1.com', 'client-1', 'marketing', 'client1-pool', 'vmta-client1-1', 'active', 100),
('45.123.10.2', 'sos-mail-2.com', 'client-1', 'marketing', 'client1-pool', 'vmta-client1-2', 'active', 100),
('45.123.10.3', 'sos-mail-3.com', 'client-1', 'marketing', 'client1-pool', 'vmta-client1-3', 'active', 100),
-- ... (37 autres IPs active)

-- Warming (7 IPs)
('45.123.10.41', 'sos-mail-41.com', 'client-1', 'marketing', 'client1-pool', 'vmta-client1-41', 'warming', 50),
('45.123.10.42', 'sos-mail-42.com', 'client-1', 'marketing', 'client1-pool', 'vmta-client1-42', 'warming', 30),
-- ... (5 autres IPs warming)

-- Standby (3 IPs)
('45.123.10.48', 'sos-mail-48.com', 'client-1', 'marketing', 'client1-pool', 'vmta-client1-48', 'standby', 0),
('45.123.10.49', 'sos-mail-49.com', 'client-1', 'marketing', 'client1-pool', 'vmta-client1-49', 'standby', 0),
('45.123.10.50', 'sos-mail-50.com', 'client-1', 'marketing', 'client1-pool', 'vmta-client1-50', 'standby', 0);

-- Pool Client 2 (50 IPs)
INSERT INTO ips (address, hostname, tenant, purpose, pool_name, vmta_name, status, weight) VALUES
('45.124.20.1', 'client2-mail-1.com', 'client-2', 'marketing', 'client2-pool', 'vmta-client2-1', 'active', 100),
('45.124.20.2', 'client2-mail-2.com', 'client-2', 'marketing', 'client2-pool', 'vmta-client2-2', 'active', 100),
-- ... (48 autres IPs)
```

---

## 4. DOMAINES MULTIPLES ROTATIFS

### 4.1 Stratégie Domaines

**Domaines Marque** (JAMAIS utilisés pour envoi) :
- client1-domain.com → Site web Client 1
- client2-domain.com → Site web Client 2

**Domaines Envoi** (cold email) :

**Client 1 (50 domaines)** :
```
sos-mail.com          → IP 45.123.10.1
sos-newsletter.com    → IP 45.123.10.2
sos-info.com          → IP 45.123.10.3
sos-contact.com       → IP 45.123.10.4
sos-services.com      → IP 45.123.10.5
...
client1-mail.com
client1-news.com
client1-contact.com
...
(50 domaines au total, 1 par IP)
```

**Client 2 (50 domaines)** :
```
client2-mail.com      → IP 45.124.20.1
client2-newsletter.com → IP 45.124.20.2
client2-info.com      → IP 45.124.20.3
client2-contact.com   → IP 45.124.20.4
...
(50 domaines au total, 1 par IP)
```

### 4.2 Table `domains`

```sql
-- Table existante (déjà dans email-engine)
CREATE TABLE domains (
    id SERIAL PRIMARY KEY,

    -- Identity
    name VARCHAR(255) UNIQUE NOT NULL,       -- 'sos-mail.com'

    -- Tenant (NOUVEAU)
    tenant VARCHAR(50) NOT NULL,             -- 'client-1', 'client-2'

    -- Purpose
    purpose VARCHAR(20) DEFAULT 'marketing', -- 'marketing', 'transactional'

    -- IP association
    ip_id INTEGER REFERENCES ips(id),        -- IP dédiée

    -- DNS config
    dkim_selector VARCHAR(63) DEFAULT 'default',
    dkim_key_path VARCHAR(500),              -- '/etc/pmta/dkim/sos-mail.com.key'

    -- DNS validation
    spf_valid BOOLEAN DEFAULT FALSE,
    dkim_valid BOOLEAN DEFAULT FALSE,
    dmarc_valid BOOLEAN DEFAULT FALSE,
    ptr_valid BOOLEAN DEFAULT FALSE,
    last_dns_check TIMESTAMP,

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT uq_domain_tenant UNIQUE (name, tenant)
);

CREATE INDEX idx_domains_tenant ON domains(tenant);
CREATE INDEX idx_domains_ip_id ON domains(ip_id);
```

### 4.3 Mapping IP ↔ Domaine

```python
# Chaque IP a 1 domaine dédié (1:1)
# Rotation IP = Rotation domaine automatique

ip_domain_mapping = {
    # Client 1
    '45.123.10.1': 'sos-mail.com',
    '45.123.10.2': 'sos-newsletter.com',
    '45.123.10.3': 'sos-info.com',
    # ...

    # Client 2
    '45.124.20.1': 'client2-mail.com',
    '45.124.20.2': 'client2-newsletter.com',
    # ...
}
```

---

## 5. ISOLATION MULTI-TENANT

### 5.1 Séparation Complète

```
┌─────────────────────────────────────────────────────────────────┐
│                      TENANT: SOS-EXPAT                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  MailWizz Instance:    mailwizz-sos.com (89.167.2.10)          │
│  PowerMTA Pool:        sos-pool (45.123.10.1-50)               │
│  Domaines:             sos-mail.com, sos-newsletter.com, etc.  │
│  Contacts:             tenant_id='client-1'                     │
│  Campaigns:            tenant_id='client-1'                     │
│  Templates:            tenant_id='client-1'                     │
│                                                                 │
│  AUCUN lien avec Client 2 (IPs, domaines, data complètement   │
│  séparés)                                                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                       TENANT: ULIXAI                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  MailWizz Instance:    mailwizz-client2.com (89.167.3.10)      │
│  PowerMTA Pool:        client2-pool (45.124.20.1-50)           │
│  Domaines:             client2-mail.com, client2-news.com, etc.│
│  Contacts:             tenant_id='client-2'                     │
│  Campaigns:            tenant_id='client-2'                     │
│  Templates:            tenant_id='client-2'                     │
│                                                                 │
│  AUCUN lien avec Client 1                                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 Configuration PowerMTA (par tenant)

```ini
# /etc/pmta/config

# ─────────────────────────────────────────────────────────
# POOL SOS-EXPAT
# ─────────────────────────────────────────────────────────

<virtual-mta sos-vmta-1>
    smtp-source-host sos-mail.com 45.123.10.1
    domain-key default,sos-mail.com,/etc/pmta/dkim/sos-mail.com.key
</virtual-mta>

<virtual-mta sos-vmta-2>
    smtp-source-host sos-newsletter.com 45.123.10.2
    domain-key default,sos-newsletter.com,/etc/pmta/dkim/sos-newsletter.com.key
</virtual-mta>

# ... (48 autres VMTAs Client 1)

# Pool Client 1 (rotation weighted)
<virtual-mta-pool client1-pool>
    virtual-mta sos-vmta-1 weight 100    # Active
    virtual-mta sos-vmta-2 weight 100    # Active
    virtual-mta sos-vmta-3 weight 100    # Active
    # ...
    virtual-mta sos-vmta-41 weight 50    # Warming
    virtual-mta sos-vmta-42 weight 30    # Warming
    # Standby IPs (weight 0 = pas utilisées)
</virtual-mta-pool>

# ─────────────────────────────────────────────────────────
# POOL ULIXAI
# ─────────────────────────────────────────────────────────

<virtual-mta vmta-client2-1>
    smtp-source-host client2-mail.com 45.124.20.1
    domain-key default,client2-mail.com,/etc/pmta/dkim/client2-mail.com.key
</virtual-mta>

# ... (49 autres VMTAs Client 2)

<virtual-mta-pool client2-pool>
    virtual-mta vmta-client2-1 weight 100
    virtual-mta vmta-client2-2 weight 100
    # ...
</virtual-mta-pool>

# ─────────────────────────────────────────────────────────
# ROUTING (MailWizz → PowerMTA pool)
# ─────────────────────────────────────────────────────────

# MailWizz Client 1 (89.167.2.10) → client1-pool
<source 89.167.2.10>
    always-allow-relaying yes
    process-x-virtual-mta yes
    default-virtual-mta-pool client1-pool
</source>

# MailWizz Client 2 (89.167.3.10) → client2-pool
<source 89.167.3.10>
    always-allow-relaying yes
    process-x-virtual-mta yes
    default-virtual-mta-pool client2-pool
</source>
```

---

## 6. WARMUP IPS AUTOMATISÉ

### 6.1 Plan Warmup 6 Semaines (par IP)

**Objectif** : Construire réputation IP progressivement

| Semaine | Quota/jour | Envois cumulés | Status |
|---------|------------|----------------|--------|
| Week 1  | 50         | 350            | WARMING |
| Week 2  | 100        | 1,050          | WARMING |
| Week 3  | 250        | 2,800          | WARMING |
| Week 4  | 500        | 6,300          | WARMING |
| Week 5  | 1,000      | 13,300         | WARMING |
| Week 6  | 2,000      | 27,300         | ACTIVE  |
| Week 6+ | 10,000+    | ∞              | ACTIVE  |

### 6.2 Table `warmup_plans` (existante)

```sql
-- Table existante (déjà dans email-engine)
CREATE TABLE warmup_plans (
    id SERIAL PRIMARY KEY,

    -- IP association
    ip_id INTEGER REFERENCES ips(id) UNIQUE NOT NULL,

    -- Warmup phase
    phase VARCHAR(20) DEFAULT 'week_1',      -- 'week_1' → 'week_6'
    started_at TIMESTAMP DEFAULT NOW(),

    -- Quotas
    current_daily_quota INTEGER DEFAULT 50,
    target_daily_quota INTEGER DEFAULT 10000,

    -- Safety metrics
    bounce_rate_7d FLOAT DEFAULT 0.0,        -- Taux bounce 7 derniers jours
    spam_rate_7d FLOAT DEFAULT 0.0,          -- Taux spam complaints
    open_rate_7d FLOAT DEFAULT 0.0,          -- Taux ouverture

    -- Pause (si metrics dégradées)
    paused BOOLEAN DEFAULT FALSE,
    pause_until TIMESTAMP
);

-- Warmup daily stats (déjà existant)
CREATE TABLE warmup_daily_stats (
    id SERIAL PRIMARY KEY,
    plan_id INTEGER REFERENCES warmup_plans(id) NOT NULL,
    date DATE NOT NULL,

    -- Stats quotidiennes
    sent INTEGER DEFAULT 0,
    delivered INTEGER DEFAULT 0,
    bounced INTEGER DEFAULT 0,
    complaints INTEGER DEFAULT 0,
    opens INTEGER DEFAULT 0,
    clicks INTEGER DEFAULT 0,

    CONSTRAINT uq_plan_date UNIQUE (plan_id, date)
);
```

### 6.3 Service Warmup Automatique

```python
# src/domain/services/ip_warmup_service.py

class IPWarmupService:
    """
    Gestion warmup IPs automatisé.

    Logique:
    1. Daily cron (00:00 UTC)
    2. Pour chaque IP en warmup:
       - Avancer phase si conditions OK
       - Augmenter quota
       - Pause si bounce/spam rate élevé
    """

    WARMUP_SCHEDULE = {
        'week_1': {'daily_quota': 50, 'min_days': 7},
        'week_2': {'daily_quota': 100, 'min_days': 7},
        'week_3': {'daily_quota': 250, 'min_days': 7},
        'week_4': {'daily_quota': 500, 'min_days': 7},
        'week_5': {'daily_quota': 1000, 'min_days': 7},
        'week_6': {'daily_quota': 2000, 'min_days': 7},
        'active': {'daily_quota': 10000, 'min_days': 999},
    }

    # Safety thresholds
    MAX_BOUNCE_RATE = 0.05   # 5%
    MAX_SPAM_RATE = 0.001    # 0.1%
    MIN_OPEN_RATE = 0.10     # 10%

    async def advance_warmup_phases(self):
        """Avance phases warmup pour toutes IPs."""

        # Get all warmup plans (not paused)
        plans = await self.uow.warmup_plans.find_active()

        for plan in plans:
            await self._advance_plan(plan)

    async def _advance_plan(self, plan: WarmupPlan):
        """Avance phase warmup pour 1 IP."""

        # 1. Check safety metrics
        if not self._is_safe_to_advance(plan):
            # Pause warmup
            plan.pause(days=7)
            await self.telegram.alert(
                f"⚠️ IP {plan.ip.address} paused: "
                f"bounce={plan.bounce_rate_7d:.2%} "
                f"spam={plan.spam_rate_7d:.2%}"
            )
            return

        # 2. Check if enough days in current phase
        days_in_phase = (datetime.now() - plan.phase_changed_at).days

        current_phase_config = self.WARMUP_SCHEDULE[plan.phase]

        if days_in_phase < current_phase_config['min_days']:
            # Pas encore assez de jours
            return

        # 3. Advance to next phase
        next_phase = self._get_next_phase(plan.phase)

        if next_phase:
            plan.advance_phase(next_phase)

            next_quota = self.WARMUP_SCHEDULE[next_phase]['daily_quota']
            plan.current_daily_quota = next_quota

            await self.uow.commit()

            # Sync quota to MailWizz
            await self.mailwizz_sync.update_delivery_server_quota(
                plan.ip.mailwizz_server_id,
                next_quota
            )

            await self.telegram.alert(
                f"✅ IP {plan.ip.address} advanced to {next_phase} "
                f"(quota: {next_quota}/day)"
            )

    def _is_safe_to_advance(self, plan: WarmupPlan) -> bool:
        """Check si metrics sont OK."""
        return (
            plan.bounce_rate_7d <= self.MAX_BOUNCE_RATE and
            plan.spam_rate_7d <= self.MAX_SPAM_RATE and
            plan.open_rate_7d >= self.MIN_OPEN_RATE
        )

    def _get_next_phase(self, current_phase: str) -> str | None:
        """Retourne phase suivante."""
        phases = ['week_1', 'week_2', 'week_3', 'week_4', 'week_5', 'week_6', 'active']

        try:
            idx = phases.index(current_phase)
            return phases[idx + 1] if idx + 1 < len(phases) else None
        except ValueError:
            return None
```

---

## 7. ROTATION INTELLIGENTE

### 7.1 Modes de Rotation

**1. Round-Robin (équitable)** :
```python
# Chaque IP utilisée à tour de rôle
ips = ['45.123.10.1', '45.123.10.2', '45.123.10.3']
current_index = 0

def get_next_ip():
    global current_index
    ip = ips[current_index]
    current_index = (current_index + 1) % len(ips)
    return ip
```

**2. Weighted Random (pondéré)** :
```python
# IPs avec poids différents (warming vs active)
ips_weighted = [
    ('45.123.10.1', 100),  # Active
    ('45.123.10.2', 100),  # Active
    ('45.123.10.3', 50),   # Warming week 5
    ('45.123.10.4', 30),   # Warming week 3
]

def get_weighted_ip():
    total = sum(weight for _, weight in ips_weighted)
    rand = random.randint(0, total - 1)

    for ip, weight in ips_weighted:
        if rand < weight:
            return ip
        rand -= weight
```

**3. Least-Used (équilibrage)** :
```python
# Choisir IP avec le moins d'envois récents
async def get_least_used_ip(tenant: str):
    # Query IPs avec sent count (last 1h)
    ip = await db.query("""
        SELECT ip.address
        FROM ips ip
        LEFT JOIN contact_events ce ON ce.ip_address = ip.address
            AND ce.timestamp > NOW() - INTERVAL '1 hour'
        WHERE ip.tenant = :tenant
          AND ip.status = 'active'
        GROUP BY ip.id, ip.address
        ORDER BY COUNT(ce.id) ASC
        LIMIT 1
    """, {'tenant': tenant})

    return ip
```

### 7.2 Service Rotation

```python
# src/domain/services/ip_rotation_service.py

class IPRotationService:
    """Sélection IP intelligente pour envoi."""

    def __init__(
        self,
        uow: IUnitOfWork,
        cache: CacheService
    ):
        self.uow = uow
        self.cache = cache

    async def select_ip_for_campaign(
        self,
        tenant: str,
        campaign_id: str,
        mode: str = 'weighted_random'
    ) -> IP:
        """
        Sélectionne IP optimale pour campagne.

        Args:
            tenant: 'client-1' ou 'client-2'
            campaign_id: ID campagne
            mode: 'round_robin', 'weighted_random', 'least_used'

        Returns:
            IP entity
        """

        # 1. Get active IPs for tenant (cached)
        cache_key = f"ips:active:{tenant}"
        ips = await self.cache.get(cache_key)

        if not ips:
            ips = await self.uow.ips.find_by_specification(
                ActiveIPsForTenant(tenant)
            )
            await self.cache.set(cache_key, ips, ttl=300)  # 5min

        if not ips:
            raise NoActiveIPError(f"No active IPs for tenant {tenant}")

        # 2. Select based on mode
        if mode == 'round_robin':
            ip = self._select_round_robin(ips, tenant)

        elif mode == 'weighted_random':
            ip = self._select_weighted_random(ips)

        elif mode == 'least_used':
            ip = await self._select_least_used(ips)

        else:
            raise ValueError(f"Unknown rotation mode: {mode}")

        return ip

    def _select_weighted_random(self, ips: List[IP]) -> IP:
        """Weighted random selection."""
        weights = [ip.weight for ip in ips]
        return random.choices(ips, weights=weights, k=1)[0]

    async def _select_least_used(self, ips: List[IP]) -> IP:
        """Least used in last hour."""
        # Query sent count per IP (last 1h)
        ip_usage = await self.uow.contact_events.count_by_ip_last_hour(
            [ip.address for ip in ips]
        )

        # Sort by usage (ascending)
        ips_sorted = sorted(
            ips,
            key=lambda ip: ip_usage.get(ip.address, 0)
        )

        return ips_sorted[0]

    def _select_round_robin(self, ips: List[IP], tenant: str) -> IP:
        """Round-robin selection (stateful)."""
        # Get current index from cache/db
        cache_key = f"ip_rotation:round_robin:{tenant}"
        current_index = await self.cache.get(cache_key) or 0

        ip = ips[current_index % len(ips)]

        # Increment index
        await self.cache.set(
            cache_key,
            (current_index + 1) % len(ips),
            ttl=3600
        )

        return ip
```

---

## 8. MONITORING & FAILOVER

### 8.1 Blacklist Monitoring Automatique

**Job cron (toutes les 4h)** :

```python
# src/infrastructure/background/tasks/monitoring_tasks.py

@celery_app.task(name='check_blacklists_all_ips')
async def check_blacklists_all_ips():
    """
    Check blacklists pour toutes IPs (4h).

    Blacklists checkées:
    - Spamhaus (ZEN)
    - SpamCop
    - SORBS
    - Barracuda
    - UCEPROTECT
    - ... (9 total)
    """

    async with UnitOfWork() as uow:
        # Get all active IPs
        ips = await uow.ips.find_by_specification(
            ActiveOrWarmingIPs()
        )

        for ip in ips:
            result = await blacklist_checker.check_ip(ip.address)

            if result.is_blacklisted:
                # BLACKLIST DÉTECTÉE !
                await handle_blacklist_detection(ip, result)

async def handle_blacklist_detection(ip: IP, result: BlacklistResult):
    """Handle IP blacklist detection."""

    async with UnitOfWork() as uow:
        # 1. Mettre IP en quarantine
        ip.quarantine(days=7)
        ip.blacklisted_on = result.blacklists  # ['spamhaus', 'spamcop']

        await uow.commit()

        # 2. Activer IP standby (failover automatique)
        standby_ip = await uow.ips.get_next_standby(ip.tenant)

        if standby_ip:
            standby_ip.activate()
            await uow.commit()

            # Sync PowerMTA config
            await powermta_manager.update_pool_config(ip.tenant)

            await telegram.alert(
                f"🚨 IP {ip.address} BLACKLISTED on {result.blacklists}\n"
                f"✅ Standby IP {standby_ip.address} activated\n"
                f"⏸️ Quarantine: 7 days"
            )
        else:
            await telegram.alert(
                f"🚨🚨 IP {ip.address} BLACKLISTED\n"
                f"❌ NO STANDBY IP AVAILABLE\n"
                f"ACTION REQUIRED"
            )

        # 3. Create blacklist event
        event = BlacklistEvent(
            ip_id=ip.id,
            blacklist_name=','.join(result.blacklists),
            auto_recovered=bool(standby_ip)
        )
        await uow.blacklist_events.add(event)
        await uow.commit()
```

### 8.2 Failover Automatique

**Scénario** :
1. IP `45.123.10.5` détectée sur Spamhaus
2. Email Engine → Quarantine IP (7 jours)
3. Email Engine → Active standby IP `45.123.10.48`
4. Email Engine → Update PowerMTA config (retire IP blacklistée, ajoute standby)
5. Email Engine → Reload PowerMTA config
6. Alerte Telegram envoyée

**Config PowerMTA mise à jour automatiquement** :
```ini
# AVANT blacklist
<virtual-mta-pool sos-pool>
    virtual-mta sos-vmta-5 weight 100    # IP blacklistée
    virtual-mta sos-vmta-48 weight 0     # Standby
</virtual-mta-pool>

# APRÈS blacklist (auto-update)
<virtual-mta-pool sos-pool>
    # sos-vmta-5 REMOVED (quarantine)
    virtual-mta sos-vmta-48 weight 100   # Standby → ACTIVE
</virtual-mta-pool>
```

---

## 9. DNS CONFIGURATION

### 9.1 DNS Records (par domaine)

**Pour chaque domaine envoi** (exemple: `sos-mail.com`) :

```dns
; A Record (IP dédiée)
@       IN  A       45.123.10.1

; MX Record (pas nécessaire pour cold email, mais recommandé)
@       IN  MX  10  mail.sos-mail.com.
mail    IN  A       45.123.10.1

; PTR Record (Reverse DNS) - CRUCIAL
; Configuré chez provider IPs (Hetzner/OVH)
; 45.123.10.1 → sos-mail.com

; SPF Record
@       IN  TXT     "v=spf1 ip4:45.123.10.1 -all"

; DKIM Record
default._domainkey  IN  TXT  "v=DKIM1; k=rsa; p=MIGfMA0GCSqGSIb3DQEBAQUAA..."

; DMARC Record
_dmarc  IN  TXT     "v=DMARC1; p=quarantine; rua=mailto:dmarc@sos-mail.com"
```

### 9.2 Validation DNS Automatique

```python
# Job cron (quotidien - 06:00 UTC)
@celery_app.task(name='validate_dns_all_domains')
async def validate_dns_all_domains():
    """Validate DNS pour tous domaines."""

    async with UnitOfWork() as uow:
        domains = await uow.domains.get_all()

        for domain in domains:
            result = await dns_validator.validate_domain(domain)

            domain.spf_valid = result.spf_valid
            domain.dkim_valid = result.dkim_valid
            domain.dmarc_valid = result.dmarc_valid
            domain.ptr_valid = result.ptr_valid
            domain.last_dns_check = datetime.now()

            if not result.all_valid():
                await telegram.alert(
                    f"⚠️ DNS issues for {domain.name}:\n"
                    f"SPF: {'✅' if result.spf_valid else '❌'}\n"
                    f"DKIM: {'✅' if result.dkim_valid else '❌'}\n"
                    f"DMARC: {'✅' if result.dmarc_valid else '❌'}\n"
                    f"PTR: {'✅' if result.ptr_valid else '❌'}"
                )

        await uow.commit()
```

---

## 10. DÉPLOIEMENT PRODUCTION

### 10.1 Checklist Déploiement

**Serveur 1 (Email Engine API)** :
```bash
# 1. Setup server
ssh root@89.167.1.10
apt update && apt upgrade -y
apt install -y postgresql-15 redis nginx python3.11 git

# 2. Clone repo
git clone https://github.com/your-org/email-engine.git
cd email-engine

# 3. Install dependencies
pip install -r requirements.txt

# 4. Setup database
createdb email_engine
alembic upgrade head

# 5. Seed data (IPs, domaines, tenants)
python scripts/seed_data.py --tenant client-1
python scripts/seed_data.py --tenant client-2

# 6. Start services
systemctl start email-engine-api
systemctl start celery-workers
systemctl start nginx
```

**Serveur 2A/2B (MailWizz)** :
```bash
# Installation MailWizz (standard)
# Configuration:
# - Domain: mailwizz-sos.com
# - MySQL database
# - Delivery server: PowerMTA (100.1.1.1:25)
```

**Serveur 3 (PowerMTA)** :
```bash
# 1. Install PowerMTA
# (licence commerciale requise)

# 2. Configure IPs pool
# /etc/pmta/config (généré par Email Engine)

# 3. Setup DKIM keys (50 domaines Client 1 + 50 Client 2)
for domain in sos-mail-{1..50}.com; do
    openssl genrsa -out /etc/pmta/dkim/${domain}.key 2048
    openssl rsa -in /etc/pmta/dkim/${domain}.key -pubout > /etc/pmta/dkim/${domain}.pub
done

# 4. Reload PowerMTA
pmta reload
```

---

## ✅ RÉSUMÉ ARCHITECTURE INFRASTRUCTURE

### Infrastructure Physique

✅ **3 Serveurs séparés** :
- Serveur 1 : Email Engine API (orchestration)
- Serveur 2A/2B : MailWizz Client 1 + Client 2
- Serveur 3 : PowerMTA + Pool 100 IPs

✅ **100 IPs dédiées** :
- 50 IPs Client 1 (rotation)
- 50 IPs Client 2 (rotation)
- Warmup 6 semaines automatisé
- Failover automatique (standby IPs)

✅ **100 Domaines rotatifs** :
- 1 domaine par IP (1:1 mapping)
- DNS configurés (SPF, DKIM, DMARC, PTR)
- Validation automatique quotidienne

✅ **Isolation Multi-Tenant** :
- Client 1 ≠ Client 2 (aucun lien IPs/domaines)
- Pools séparés dans PowerMTA
- Instances MailWizz séparées

✅ **Monitoring & Failover** :
- Blacklist check toutes les 4h
- Quarantine automatique si détection
- Activation standby IP automatique
- Alertes Telegram temps réel

---

**Tu veux que je continue avec** :
- Migration plan détaillé ?
- Scripts seed data (IPs, domaines) ?
- PowerMTA config generator ?

**Ou on implémente maintenant ?** 🚀
