# 🎯 CLARIFICATION FINALE : MailWizz vs email-engine

**Date** : 16 février 2026
**Question** : MailWizz fait déjà tout (répondeurs, segments, tracking), alors pourquoi email-engine ?

---

## ✅ CE QUE MAILWIZZ FAIT **DÉJÀ** (backup-cold)

### 1. Email Marketing Complet

```
✅ Campagnes
   ├─ One-time sends
   ├─ Scheduled campaigns
   └─ A/B testing

✅ Autoresponders (Séquences)
   ├─ Welcome series
   ├─ Drip campaigns
   ├─ Time-based triggers
   └─ Action-based triggers

✅ Segments
   ├─ Filtres dynamiques (âge, pays, etc.)
   ├─ Comportemental (opened, clicked, etc.)
   └─ Custom fields

✅ Tracking
   ├─ Opens (pixel tracking)
   ├─ Clicks (link tracking)
   ├─ Bounces (hard/soft)
   ├─ Unsubscribes
   └─ Spam complaints

✅ Intégrations Site Web
   ├─ Forms (opt-in)
   ├─ Webhooks
   ├─ API
   └─ Landing pages

✅ Templates
   ├─ Drag & drop builder
   ├─ HTML editor
   └─ Gallery templates

✅ Lists Management
   ├─ Import/Export CSV
   ├─ Custom fields
   ├─ Suppression lists
   └─ Blacklists locales
```

**VERDICT : MailWizz est un EMAIL MARKETING PLATFORM COMPLET** ✅

---

## ❌ CE QUE MAILWIZZ NE FAIT **PAS**

### 1. IP Warmup Automatique

**MailWizz :**
```
❌ Pas de warmup automatique
❌ Tu dois MANUELLEMENT:
   1. Créer delivery server
   2. Set quota à 50/jour (semaine 1)
   3. ATTENDRE 7 jours
   4. REVENIR changer quota à 200/jour (semaine 2)
   5. ATTENDRE 7 jours
   6. REVENIR changer quota à 500/jour (semaine 3)
   ... répéter pendant 6 semaines

❌ Si tu oublies une semaine → IP sous-utilisée
❌ Si tu augmentes trop vite → IP blacklistée
```

**email-engine :**
```
✅ POST /api/v2/ips {"address": "1.2.3.4", "purpose": "marketing"}
✅ email-engine fait TOUT automatiquement:
   Week 1: Set quota 50/jour
   Week 2: Set quota 200/jour
   Week 3: Set quota 500/jour
   Week 4: Set quota 1500/jour
   Week 5: Set quota 5000/jour
   Week 6+: Set quota 10000/jour

✅ Sync automatique avec MailWizz (hourly)
✅ Alerte Telegram quand warmup terminé
```

### 2. Blacklist Monitoring

**MailWizz :**
```
❌ Aucun check blacklist automatique
❌ Tu dois MANUELLEMENT:
   1. Ouvrir mxtoolbox.com
   2. Enter ton IP
   3. Check les 9 RBL une par une
   4. Répéter pour chaque IP
   5. Répéter chaque jour

❌ Si IP blacklistée → tu le découvres trop tard (parfois 1 semaine après!)
```

**email-engine :**
```
✅ Cron toutes les 4h
✅ Check automatique 9 RBL:
   - SpamHaus (ZEN, XBL, PBL, SBL)
   - SpamCop
   - SORBS
   - Barracuda
   - UCEPROTECT
   - PSBL

✅ Si blacklist détectée:
   ├─ Alerte Telegram immédiate
   ├─ IP mise en STANDBY automatiquement
   ├─ Trafic routé vers autres IPs
   └─ Record dans database (audit trail)

✅ Détection : 4h max (au lieu de plusieurs jours)
```

### 3. DNS Validation

**MailWizz :**
```
❌ Pas de validation DNS automatique
❌ Tu dois MANUELLEMENT vérifier:
   - SPF record (dig TXT domain.com)
   - DKIM record (dig TXT default._domainkey.domain.com)
   - DMARC record (dig TXT _dmarc.domain.com)
   - PTR record (dig -x IP_ADDRESS)
   - MX record (dig MX domain.com)

❌ Si erreur DNS → Bounces élevés → Réputation ruinée
```

**email-engine :**
```
✅ POST /api/v2/domains/validate {"domain": "sos-mail.com"}
✅ email-engine vérifie AUTOMATIQUEMENT:
   ├─ SPF ✅ v=spf1 ip4:1.2.3.4 ~all
   ├─ DKIM ✅ k=rsa; p=MIGfMA0GCS...
   ├─ DMARC ✅ v=DMARC1; p=quarantine
   ├─ PTR ✅ 1.2.3.4 → mail.sos-mail.com
   └─ MX ✅ 10 mail.sos-mail.com

✅ Retourne rapport détaillé:
   {
     "spf": {"valid": true, "record": "..."},
     "dkim": {"valid": true, "selector": "default"},
     "dmarc": {"valid": true, "policy": "quarantine"},
     "ptr": {"valid": true, "hostname": "mail.sos-mail.com"},
     "mx": {"valid": true, "records": [...]}
   }
```

### 4. IP Lifecycle Management

**MailWizz :**
```
❌ Pas de gestion cycle de vie IPs
❌ Tu dois MANUELLEMENT gérer:
   - Quand retirer une IP (RETIRING)
   - Quand mettre en repos (RESTING)
   - Combien de temps repos (best practice: 30 jours)
   - Quand relancer warmup (WARMING)

❌ Pas de tracking historique
❌ Pas de rotation automatique
```

**email-engine :**
```
✅ State machine automatique:

STANDBY (nouvelle IP)
   ↓ (POST /api/v2/ips/{id}/warmup)
WARMING (6 semaines)
   ↓ (auto après 6 semaines)
ACTIVE (production)
   ↓ (si blacklist OU volontaire)
RETIRING (diminution progressive quotas)
   ↓ (après X jours)
RESTING (30 jours off complet)
   ↓ (après 30 jours)
STANDBY (7 jours monitoring)
   ↓ (si clean)
WARMING (nouveau cycle warmup)

✅ Tracking complet dans database
✅ Métriques par IP (sent, delivered, bounced, complaints)
✅ Rotation automatique selon load
```

### 5. PowerMTA Config Management

**MailWizz :**
```
❌ Aucune gestion PowerMTA
❌ Tu dois MANUELLEMENT:
   1. SSH sur serveur PowerMTA
   2. vim /etc/pmta/config
   3. Modifier VirtualMTA quotas
   4. pmta reload (peut drop connections!)
   5. Espérer que ça marche

❌ Pas de version control
❌ Pas de rollback si erreur
❌ Risque de casser prod
```

**email-engine :**
```
✅ PUT /api/v2/powermta/config
   {
     "virtual_mtas": [
       {
         "name": "pmta-vmta0",
         "ip": "1.2.3.4",
         "hostname": "mail1.sos-mail.com",
         "quota": "50/day",
         "dkim_key": "/path/to/dkim.pem"
       }
     ]
   }

✅ email-engine:
   ├─ Génère config PowerMTA
   ├─ Valide syntax
   ├─ Backup config actuelle
   ├─ Deploy nouvelle config
   ├─ Reload graceful (zero downtime)
   └─ Rollback si erreur

✅ Git versioning
✅ API-driven (no SSH needed)
✅ Audit trail complet
```

### 6. Multi-Tenant Isolation

**MailWizz :**
```
❌ 1 instance = 1 customer à la fois
❌ Pour gérer SOS-Expat + Ulixai:
   - Option 1: 2 instances MailWizz séparées
     ├─ mail.sos-expat.com
     └─ mail.ulixai.com
     → Coût x2, maintenance x2

   - Option 2: Tout mélanger dans 1 instance
     → SOS peut voir données Ulixai (BAD!)

❌ Pas d'isolation quotas
❌ Pas d'isolation IPs
```

**email-engine :**
```
✅ Multi-tenant natif:

POST /api/v2/tenants
[
  {
    "slug": "sos-expat",
    "name": "SOS Expat",
    "brand_domain": "sos-expat.com",
    "sending_domain_base": "sos-mail.com"
  },
  {
    "slug": "ulixai",
    "name": "Ulixai",
    "brand_domain": "ulixai.com",
    "sending_domain_base": "ulixai-mail.com"
  }
]

✅ Isolation COMPLÈTE:
   Tenant 1 (SOS-Expat)
   ├─ IPs dédiées: [1.2.3.4, 1.2.3.5]
   ├─ Sending domains: [sos-mail.com]
   ├─ Quotas: 5000/jour
   ├─ MailWizz instance: mail.sos-expat.com
   └─ Base de données isolée

   Tenant 2 (Ulixai)
   ├─ IPs dédiées: [5.6.7.8, 5.6.7.9]
   ├─ Sending domains: [ulixai-mail.com]
   ├─ Quotas: 10000/jour
   ├─ MailWizz instance: mail.ulixai.com
   └─ Base de données isolée

✅ SOS ne peut PAS voir Ulixai
✅ Problème SOS n'affecte PAS Ulixai
✅ Quotas séparés, métriques séparées
```

### 7. Monitoring & Alerting

**MailWizz :**
```
❌ Monitoring basique seulement:
   - Logs Apache/Nginx
   - Logs MySQL
   - Stats campagnes dans UI

❌ Pas de métriques infrastructure:
   - CPU usage?
   - RAM usage?
   - Disk usage?
   - Queue size?
   - Response time?

❌ Pas d'alertes proactives:
   - IP blacklistée → tu le découvres trop tard
   - Disk plein → campagne échoue silencieusement
   - MySQL slow → pas de notification
```

**email-engine :**
```
✅ Monitoring complet (Prometheus + Grafana):

Métriques collectées (13 metrics):
  ├─ email_engine_ips_total (par status)
  ├─ email_engine_warmup_progress (%)
  ├─ email_engine_blacklist_checks_total
  ├─ email_engine_blacklist_listings_total
  ├─ email_engine_dns_validations_total
  ├─ email_engine_emails_sent_total
  ├─ email_engine_bounce_rate
  ├─ email_engine_complaint_rate
  ├─ email_engine_api_requests_total
  ├─ email_engine_api_request_duration_seconds
  ├─ email_engine_db_connections_active
  ├─ email_engine_celery_tasks_total
  └─ email_engine_system_cpu_percent

✅ Alertes Telegram temps réel:
  ├─ IP blacklistée → Alerte immédiate
  ├─ Bounce rate > 5% → Warning
  ├─ Complaint rate > 0.1% → Critical
  ├─ Disk > 80% → Warning
  ├─ Warmup terminé → Info
  └─ API error rate > 1% → Critical

✅ Dashboards Grafana:
  ├─ Overview (santé globale)
  ├─ IPs Dashboard (status, métriques par IP)
  ├─ Warmup Dashboard (progrès, timeline)
  ├─ Blacklists Dashboard (événements, RBL status)
  └─ API Dashboard (requests, latency, errors)
```

---

## 🎯 COMPARAISON TABLEAU

| Feature | MailWizz (backup-cold) | email-engine |
|---------|------------------------|--------------|
| **Email Marketing** |
| Campagnes | ✅ Complet | ❌ N/A (utilise MailWizz) |
| Autoresponders | ✅ Complet | ❌ N/A (utilise MailWizz) |
| Segments | ✅ Complet | ❌ N/A (utilise MailWizz) |
| Tracking (opens/clicks) | ✅ Complet | ❌ N/A (utilise MailWizz) |
| Landing pages | ✅ Complet | ❌ N/A |
| Forms | ✅ Complet | ❌ N/A |
| A/B testing | ✅ Complet | ❌ N/A |
| **Infrastructure Management** |
| IP Warmup Auto | ❌ Manuel | ✅ Auto 6 semaines |
| Blacklist Check | ❌ Manuel | ✅ Auto 6×/jour (9 RBL) |
| DNS Validation | ❌ Manuel | ✅ Auto (SPF/DKIM/DMARC/PTR) |
| IP Lifecycle | ❌ Manuel | ✅ State machine auto |
| PowerMTA Config | ❌ SSH manual | ✅ API-driven |
| Multi-tenant | ❌ 1 instance/tenant | ✅ N tenants isolés |
| Monitoring | ❌ Basique | ✅ Prometheus/Grafana |
| Alerting | ❌ Email only | ✅ Telegram temps réel |

---

## ✅ CONCLUSION

### MailWizz (backup-cold)
**Rôle** : EMAIL MARKETING PLATFORM
- ✅ Campagnes, autoresponders, segments, tracking
- ✅ Tout ce qui concerne l'EMAIL MARKETING
- ❌ Mais PAS l'infrastructure (IPs, DNS, monitoring)

### email-engine
**Rôle** : INFRASTRUCTURE ORCHESTRATOR
- ✅ Warmup IPs, blacklist check, DNS validation
- ✅ Tout ce qui concerne l'INFRASTRUCTURE
- ❌ Mais PAS l'email marketing (utilise MailWizz pour ça)

### Relation

```
┌──────────────────────────────────────┐
│     email-engine (INFRASTRUCTURE)    │
│                                      │
│  - IP Warmup (6 weeks auto)          │
│  - Blacklist Check (9 RBL, 6×/day)   │
│  - DNS Validation (SPF/DKIM/DMARC)   │
│  - PowerMTA Config (API-driven)      │
│  - Multi-tenant Isolation            │
│  - Monitoring (Prometheus/Grafana)   │
│  - Alerting (Telegram)               │
└───────────┬──────────────────────────┘
            │
            │ 1. Configure MailWizz quotas (API)
            │ 2. Configure PowerMTA (SSH/API)
            │ 3. Monitor status (logs/metrics)
            │
            ↓
┌──────────────────────────────────────┐
│      MailWizz (EMAIL MARKETING)      │
│                                      │
│  - Campaigns                         │
│  - Autoresponders                    │
│  - Segments                          │
│  - Tracking (opens/clicks)           │
│  - Landing pages                     │
│  - Forms                             │
│  - A/B testing                       │
└───────────┬──────────────────────────┘
            │
            ↓
┌──────────────────────────────────────┐
│      PowerMTA (SMTP ENGINE)          │
│                                      │
│  - SMTP sending                      │
│  - Queue management                  │
│  - Bounce processing                 │
│  - Rate limiting per ISP             │
└──────────────────────────────────────┘
```

---

## 📋 RÉPONSE À TA QUESTION

> "MailWizz fait déjà répondeurs, segments, tracking... pourquoi email-engine ?"

**RÉPONSE:**

MailWizz fait l'**EMAIL MARKETING** ✅
email-engine fait l'**INFRASTRUCTURE MANAGEMENT** ✅

**Ce sont 2 choses DIFFÉRENTES :**

| Tâche | Qui le fait ? |
|-------|--------------|
| Créer campagne | MailWizz |
| Créer autoresponder | MailWizz |
| Segmenter contacts | MailWizz |
| Tracker opens/clicks | MailWizz |
| **Warmup IP** | **email-engine** |
| **Check blacklist** | **email-engine** |
| **Valider DNS** | **email-engine** |
| **Gérer cycle vie IPs** | **email-engine** |
| **Configurer PowerMTA** | **email-engine** |
| **Monitorer infrastructure** | **email-engine** |

**Analogie:**

```
MailWizz = PILOTE (conduit la voiture)
  ├─ Décide où aller (campagnes)
  ├─ Quand accélérer (autoresponders)
  └─ Qui prendre (segments)

email-engine = MÉCANICIEN (maintient la voiture)
  ├─ Vérifie pneus (IPs warmup)
  ├─ Change huile (rotation IPs)
  ├─ Check moteur (blacklist/DNS)
  └─ Alerte si problème (monitoring)

PowerMTA = MOTEUR (fait le travail)
  └─ Envoie les emails (SMTP)
```

**Tu as besoin des TROIS pour que ça fonctionne bien!**

---

**Question finale :** C'est plus clair maintenant ? Les 2 systèmes sont complémentaires, pas redondants.
