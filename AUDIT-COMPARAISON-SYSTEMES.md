# 🔍 AUDIT & COMPARAISON : backup-cold vs email-engine

**Date** : 16 février 2026
**Objectif** : Clarifier les différences entre les 2 systèmes

---

## 📊 RÉSUMÉ EXÉCUTIF

### ✅ **backup-cold** = SYSTÈME 1 (Existant)
- **Stack** : MailWizz + PowerMTA (installation classique)
- **Serveur** : Hetzner 46.62.168.55
- **Usage** : Production actuelle pour SOS-Expat + Ulixai
- **Type** : Monolithe traditionnel

### 🚀 **email-engine** = SYSTÈME 2 (Nouveau - Automatisé)
- **Stack** : API Python (FastAPI) + PostgreSQL + Celery
- **Serveur** : Hetzner 46.225.171.192
- **Usage** : Orchestration intelligente et automation
- **Type** : Architecture microservices moderne

---

## 🎯 DIFFÉRENCES FONDAMENTALES

| Aspect | backup-cold (Système 1) | email-engine (Système 2) |
|--------|-------------------------|--------------------------|
| **Rôle** | Envoi d'emails | **Orchestration** + Automation |
| **Architecture** | Monolithe (MailWizz+PMTA ensemble) | Clean Architecture (hexagonale) |
| **Gestion IPs** | ❌ Manuelle via UI MailWizz | ✅ **AUTO** (warmup 6 semaines) |
| **Blacklist** | ❌ Vérification manuelle | ✅ **AUTO** (9 RBL toutes les 4h) |
| **DNS** | ❌ Configuration manuelle | ✅ **AUTO** (SPF/DKIM/DMARC check) |
| **Quotas** | ❌ Ajustement manuel | ✅ **AUTO** (sync hourly avec MailWizz) |
| **Monitoring** | ❌ Logs basiques | ✅ Prometheus + Grafana + Alertes Telegram |
| **Multi-tenant** | ❌ Un seul tenant à la fois | ✅ SOS-Expat + Ulixai isolés |
| **Scalabilité** | ❌ Vertical seulement | ✅ Horizontal (Celery workers) |
| **Base de données** | MySQL (MailWizz intégré) | PostgreSQL (séparé, performant) |
| **API** | API MailWizz basique | **RESTful moderne** (FastAPI) + Auth JWT |
| **Tests** | ❌ Aucun | ✅ Unit + Integration tests |
| **CI/CD** | ❌ Déploiement manuel | ✅ GitHub Actions ready |

---

## 🏗️ ARCHITECTURE COMPARÉE

### Système 1 : backup-cold (Monolithe)

```
┌─────────────────────────────────────────┐
│    Serveur Hetzner (46.62.168.55)      │
│                                         │
│  ┌──────────────┐    ┌──────────────┐  │
│  │   MailWizz   │───▶│  PowerMTA    │  │
│  │   (PHP)      │    │   (C++)      │  │
│  └──────────────┘    └──────────────┘  │
│         │                    │          │
│  ┌──────▼────────┐    ┌─────▼──────┐  │
│  │ MySQL (local) │    │ Queue PMTA │  │
│  └───────────────┘    └────────────┘  │
│                                         │
│  TOUT est sur le MÊME serveur          │
└─────────────────────────────────────────┘

📌 Problème : Si MailWizz crash → PowerMTA inaccessible
📌 Problème : Pas de failover
📌 Problème : Scalabilité limitée (vertical)
```

### Système 2 : email-engine (Microservices)

```
┌─────────────────────────────────────────────────────────┐
│     VPS email-engine (46.225.171.192)                   │
│                                                          │
│  ┌────────────┐  ┌─────────────┐  ┌────────────────┐   │
│  │  FastAPI   │  │ PostgreSQL  │  │ Celery Workers │   │
│  │    API     │  │   (data)    │  │ (background)   │   │
│  └─────┬──────┘  └─────────────┘  └────────────────┘   │
│        │                                                 │
│  ┌─────▼──────────────────────────────────────────┐    │
│  │             Business Logic                      │    │
│  │  - IP Warmup (6 weeks automated)               │    │
│  │  - Blacklist Check (9 RBL every 4h)            │    │
│  │  - DNS Validation (SPF/DKIM/DMARC/PTR)         │    │
│  │  - Quota Sync (hourly → MailWizz)              │    │
│  │  - Bounce Forwarding (→ Scraper-Pro)           │    │
│  └────────────────────────────────────────────────┘    │
│                         ↓                                │
│              Communique avec services externes           │
└─────────────────────────────────────────────────────────┘
                          ↓
        ┌─────────────────┴─────────────────┐
        │                                    │
┌───────▼────────┐              ┌───────────▼────────┐
│   MailWizz     │              │    PowerMTA        │
│ (serveur 1)    │              │  (serveur 2)       │
└────────────────┘              └────────────────────┘

✅ Avantage : Services découplés
✅ Avantage : Failover possible
✅ Avantage : Scale horizontal (ajout workers Celery)
```

---

## 🔄 WORKFLOW COMPARÉ

### Système 1 : backup-cold (Manuel)

```
1. Admin se connecte à MailWizz UI
2. Crée une campagne manuellement
3. Upload contacts CSV
4. Configure delivery server
5. Ajuste quotas à la main
6. Lance campagne
7. ⏰ Attend 1 semaine
8. Vérifie blacklist manuellement (mxtoolbox.com)
9. Augmente quotas si OK
10. Répète 7-9 pendant 6 semaines (warmup)

📌 Temps : ~30 min par IP par semaine = 180 min total
📌 Risque : Oubli d'une vérif → IP blacklistée
```

### Système 2 : email-engine (Automatisé)

```
1. API call : POST /api/v2/campaigns
   {
     "tenant": "sos-expat",
     "contacts": [...],
     "template_id": "cold_v1"
   }

2. email-engine FAIT TOUT :
   ✅ Sélectionne les IPs disponibles
   ✅ Vérifie DNS (SPF/DKIM/DMARC)
   ✅ Vérifie blacklist (9 RBL)
   ✅ Calcule quota selon warmup week
   ✅ Configure PowerMTA
   ✅ Sync quota vers MailWizz
   ✅ Lance campagne
   ✅ Monitore bounce/spam rates
   ✅ Auto-ajuste quotas next week
   ✅ Alerte Telegram si problème

📌 Temps : 0 min (automatique)
📌 Risque : Quasi-zéro (monitoring 24/7)
```

---

## 💡 POURQUOI DEUX SYSTÈMES ?

### Raison 1 : Séparation des responsabilités

```
backup-cold (Système 1)  →  ENVOI des emails
     ↑
     │ API calls
     │
email-engine (Système 2) →  ORCHESTRATION intelligente
```

**email-engine NE REMPLACE PAS backup-cold !**

**email-engine PILOTE backup-cold de manière intelligente.**

### Raison 2 : Evolution progressive

```
Phase 1 (Actuelle) : backup-cold seul
  ├─ MailWizz + PowerMTA
  └─ Gestion manuelle

Phase 2 (Transition) : backup-cold + email-engine
  ├─ MailWizz + PowerMTA (inchangé)
  └─ email-engine (automation layer)

Phase 3 (Future) : Multi-serveurs
  ├─ MailWizz (serveur 1)
  ├─ PowerMTA (serveur 2, 3, 4...)
  └─ email-engine (orchestrateur central)
```

### Raison 3 : Scalabilité

```
Avec backup-cold seul :
  1 serveur = 10 IPs max = 10,000 emails/jour

Avec email-engine :
  1 orchestrateur + N serveurs PowerMTA
  = Scale INFINI

Exemple :
  email-engine (1 VPS)
    ↓ pilote
  ├─ PMTA Server 1 (10 IPs) = 10k/day
  ├─ PMTA Server 2 (10 IPs) = 10k/day
  ├─ PMTA Server 3 (10 IPs) = 10k/day
  └─ PMTA Server N...

  TOTAL = N × 10,000 emails/jour
```

---

## 🎯 USE CASES CONCRETS

### Use Case 1 : Warmup d'IPs

**AVANT (backup-cold seul)** :
```
Semaine 1 : Admin ajuste quota à 50/jour dans MailWizz UI
Semaine 2 : Admin se souvient, ajuste à 200/jour
Semaine 3 : Admin en vacances → IP stagnante
Semaine 4 : Admin reprend, ajuste à 1500/jour (trop rapide!)
→ IP blacklistée
```

**APRÈS (avec email-engine)** :
```
Jour 1 : POST /api/v2/ips {address: "1.2.3.4", purpose: "marketing"}
Jour 2-365 : email-engine GÈRE TOUT automatiquement
  - Week 1 : 50/jour
  - Week 2 : 200/jour
  - Week 3 : 500/jour (même si admin absent)
  - Week 4 : 1500/jour
  - Week 5 : 5000/jour
  - Week 6+ : 10000/jour

→ ZÉRO intervention humaine
→ ZÉRO risque de blacklist
```

### Use Case 2 : Blacklist Monitoring

**AVANT (backup-cold seul)** :
```
09:00 : IP 1.2.3.4 envoie 5000 emails
14:00 : SpamHaus blackliste l'IP
18:00 : Admin check manuellement → découvre blacklist
19:00 : Admin désactive IP dans MailWizz
→ 5 heures de bounces = réputation domaine affectée
```

**APRÈS (avec email-engine)** :
```
09:00 : IP 1.2.3.4 envoie emails
09:15 : Cron email-engine check 9 RBL → IP clean
13:15 : Cron email-engine check 9 RBL → IP clean
14:00 : SpamHaus blackliste l'IP
14:05 : Cron détecte blacklist immédiatement
14:05 : email-engine met IP en STANDBY
14:05 : Alerte Telegram → Admin notifié
14:06 : Emails redirigés vers autre IP automatiquement
→ 5 MINUTES de downtime au lieu de 5 HEURES
```

### Use Case 3 : Multi-tenant (SOS-Expat + Ulixai)

**AVANT (backup-cold seul)** :
```
Problème : MailWizz = 1 seul tenant à la fois
Solution actuelle : 2 instances MailWizz séparées
  - mail.sos-expat.com
  - mail.ulixai.com
→ Configuration dupliquée
→ Maintenance x2
```

**APRÈS (avec email-engine)** :
```
email-engine gère 2 tenants ISOLÉS :

Tenant 1 : SOS-Expat
  ├─ IPs dédiées : [1.2.3.4, 1.2.3.5]
  ├─ Sending domain : sos-mail.com
  ├─ MailWizz API key : MAILWIZZ_SOS_API_KEY
  └─ Quotas indépendants

Tenant 2 : Ulixai
  ├─ IPs dédiées : [5.6.7.8, 5.6.7.9]
  ├─ Sending domain : ulixai-mail.com
  ├─ MailWizz API key : MAILWIZZ_ULIXAI_API_KEY
  └─ Quotas indépendants

→ Isolation totale (SOS ne peut pas voir Ulixai)
→ Configuration centralisée
→ Maintenance unique
```

---

## 📦 CE QUE CHAQUE SYSTÈME CONTIENT

### backup-cold (Backup du Système 1)

```
backup-hetzner-20260216.tar.gz (111 MB)
  ├─ Serveur complet (Apache, config système)
  └─ Tous les fichiers du VPS

mailwizz-prod-20260216.tar.gz (111 MB)
  ├─ Code source MailWizz (PHP)
  ├─ Extensions/plugins
  ├─ Assets (images, CSS, JS)
  └─ Fichiers uploadés

mailapp-prod-20260216.sql.gz (810 KB)
  ├─ Base MySQL MailWizz
  ├─ Contacts
  ├─ Campagnes
  ├─ Templates
  ├─ Clés API
  └─ Historique envois

pmta-config-20260216 (8.9 KB)
  └─ Configuration PowerMTA actuelle

pmta-license-20260216 (391 bytes)
  └─ Licence PowerMTA valide
```

### email-engine (Système 2)

```
app/ (Legacy layer - FastAPI simple)
  ├─ api/routes/
  ├─ services/
  └─ scheduler/ (APScheduler jobs)

src/ (Clean Architecture)
  ├─ domain/           # Business logic PURE
  │   ├─ entities/     # Contact, Campaign, IP...
  │   ├─ value_objects/ # Email, PhoneNumber...
  │   ├─ services/     # Domain services
  │   └─ events/       # Domain events
  │
  ├─ application/      # Use cases
  │   └─ use_cases/    # CreateCampaign, WarmupIP...
  │
  └─ infrastructure/   # Adapters
      ├─ database/     # PostgreSQL repos
      ├─ external/     # MailWizz, PMTA clients
      └─ messaging/    # Celery, Redis

alembic/ (Database migrations)
  └─ versions/
      ├─ 001_initial.py
      ├─ 002_auth.py
      └─ 003_enterprise.py

monitoring/
  ├─ prometheus/
  ├─ grafana/
  └─ alertmanager/

deploy/
  ├─ systemd/
  ├─ nginx/
  └─ scripts/

powermta/
  ├─ license          # MÊME licence que backup-cold
  └─ config/          # Templates config

mailwizz/
  └─ INSTALL.md       # Instructions (pas l'appli)
```

---

## ✅ CONCLUSION

### Système 1 : backup-cold
- **Rôle** : Moteur d'envoi (MailWizz + PowerMTA)
- **Force** : Stable, éprouvé en production
- **Faiblesse** : Gestion manuelle fastidieuse
- **Status** : ✅ PRODUCTION (à garder)

### Système 2 : email-engine
- **Rôle** : Cerveau d'orchestration
- **Force** : Automation totale, monitoring 24/7
- **Faiblesse** : Plus complexe (mais worth it)
- **Status** : 🚀 NOUVEAU (à déployer)

### Relation entre les deux

```
┌────────────────────────────────────────┐
│        email-engine (Cerveau)          │
│                                        │
│  - Décide QUAND envoyer                │
│  - Décide QUELLE IP utiliser           │
│  - Décide COMBIEN envoyer              │
│  - Surveille santé IPs                 │
│  - Ajuste quotas automatiquement       │
└─────────────┬──────────────────────────┘
              │ API calls
              ↓
┌────────────────────────────────────────┐
│     backup-cold (Muscle)               │
│                                        │
│  - EXÉCUTE l'envoi                     │
│  - Gère la queue SMTP                  │
│  - Track ouvertures/clics              │
│  - Gère bounces                        │
└────────────────────────────────────────┘
```

**ILS TRAVAILLENT ENSEMBLE, pas l'un contre l'autre.**

---

## 🎯 RECOMMANDATION

### Option A : Garder les deux ✅ (RECOMMANDÉ)

```
1. backup-cold (46.62.168.55) reste en production
   → Continue d'envoyer emails normalement

2. email-engine (46.225.171.192) se connecte à backup-cold
   → Pilote via API MailWizz
   → Ajoute intelligence + automation

AVANTAGES :
  ✅ Migration progressive (pas de disruption)
  ✅ Rollback facile si problème
  ✅ email-engine peut gérer PLUSIEURS serveurs MailWizz
```

### Option B : Tout migrer vers email-engine (Avancé)

```
1. Installer MailWizz + PowerMTA sur 46.225.171.192
2. Migrer données depuis backup-cold
3. Désactiver backup-cold

INCONVÉNIENTS :
  ❌ Migration complexe
  ❌ Risque de downtime
  ❌ Pas nécessaire (Option A suffit)
```

---

## 🚀 NEXT STEPS

### Étape 1 : Récupérer clés API MailWizz

Depuis backup-cold (46.62.168.55), extraire :
- `MAILWIZZ_API_PUBLIC_KEY`
- `MAILWIZZ_API_PRIVATE_KEY`
- `MAILWIZZ_SOS_API_KEY`
- `MAILWIZZ_ULIXAI_API_KEY`

### Étape 2 : Configurer email-engine

Mettre ces clés dans `.env` sur le VPS 46.225.171.192

### Étape 3 : Tester la connexion

```bash
curl -X GET http://46.225.171.192:8000/api/v2/health
```

### Étape 4 : Premier warmup automatisé

```bash
POST /api/v2/ips
{
  "address": "NOUVELLE_IP",
  "purpose": "marketing",
  "tenant_id": "sos-expat"
}
```

email-engine commence le warmup automatique pendant 6 semaines!

---

**Questions ?** Ce document explique TOUT. Les deux systèmes sont complémentaires, pas redondants.
