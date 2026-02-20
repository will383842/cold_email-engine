# 🚀 Email-Engine V2 - Architecture Multi-Serveurs

**Version** : 2.0.0
**Date** : 16 février 2026
**Type** : Système autonome multi-serveurs (évolution de backup-cold)

---

## 🎯 DIFFÉRENCE V1 vs V2

| Aspect | Backup-Cold (V1) | Email-Engine V2 |
|--------|------------------|-----------------|
| **Emplacement** | `Outils d'emailing/backup-cold/` | `email-engine/` (racine VS_CODE) |
| **Architecture** | Monolithe 1 serveur | Multi-serveurs (2-3 VPS) |
| **IPs** | 2 | 5 → 100+ |
| **Domaines** | 2 | 5 → 100+ |
| **Capacité** | 10K emails/jour | 500K emails/jour |
| **Warmup** | Manuel | Automatique (6 semaines) |
| **Monitoring** | Logs basiques | Prometheus + Grafana |
| **API** | MailWizz API | FastAPI moderne + MailWizz |
| **Statut** | Archive (système éteint) | Production active |

---

## 🏗️ ARCHITECTURE V2

```
┌─────────────────────────────────────────────────────────┐
│  VPS 1 : MailWizz                                       │
│  🌐 sos-holidays.com                                    │
│  ──────────────────────────────────────────────────     │
│  • MailWizz (PHP + Nginx + MySQL)                      │
│  • 106 templates HTML (de backup-cold)                 │
│  • 77 campagnes autoresponder (de backup-cold)         │
│  • API REST (pour Email-Engine)                        │
│  • Interface web (gestion campagnes)                   │
└─────────────────────────────────────────────────────────┘
              ↓ SMTP relay :2525
┌─────────────────────────────────────────────────────────┐
│  VPS 2 : PowerMTA                                       │
│  🌐 5 domaines : mail1-5.domain.com                     │
│  🔢 5 IPs actuellement (extensible 100+)                │
│  ──────────────────────────────────────────────────     │
│  • PowerMTA 5.0+ (config de backup-cold étendue)       │
│  • 5 Virtual MTAs (1 par domaine/IP)                   │
│  • DKIM signing (5 clés)                               │
│  • Queue management                                     │
└─────────────────────────────────────────────────────────┘
              ↓ SMTP :25
         Internet (Gmail, Outlook, etc.)

┌─────────────────────────────────────────────────────────┐
│  LOCAL/VPS 3 : Email-Engine API                         │
│  📍 C:\Users\willi\...\email-engine\ (développement)   │
│  📍 VPS3 (production optionnel)                         │
│  ──────────────────────────────────────────────────     │
│  • FastAPI (orchestration)                              │
│  • PostgreSQL (5 IPs, warmup plans, monitoring)        │
│  • Redis (cache + Celery)                              │
│  • Celery (9 workers background)                       │
│  • Prometheus + Grafana (dashboards)                   │
│                                                          │
│  Communique avec :                                      │
│  • MailWizz : API HTTP (sos-holidays.com/api)          │
│  • PowerMTA : SSH + config files                       │
└─────────────────────────────────────────────────────────┘
```

---

## 📂 STRUCTURE COMPLÈTE

```
email-engine/
├── 📖 README.md                        (API technique - existant)
├── 📖 README-V2-MULTI-SERVERS.md       (ce fichier - architecture V2)
├── 📖 README-DEPLOYMENT.md             (guide déploiement complet)
├── 📖 ARCHITECTURE-PRODUCTION.md       (détails VPS1+VPS2+VPS3)
│
├── 🔧 docker-compose.yml               (API locale)
├── 🔧 .env.example                     (template configuration)
│
├── 🐍 app/                             (API FastAPI - V1)
│   ├── main.py
│   ├── config.py                       (🔴 CASSÉ actuellement)
│   ├── models.py
│   └── ...
│
├── 🐍 src/                             (Clean Architecture - V2)
│   ├── domain/
│   ├── application/
│   ├── infrastructure/
│   └── presentation/
│
├── 📦 backup-source/                   (COPIE de backup-cold)
│   ├── mailwizz-prod-20260216.tar.gz   (111 MB)
│   ├── mailapp-prod-20260216.sql.gz    (810 KB)
│   ├── pmta-config-20260216            (9 KB)
│   └── pmta-license-20260216           (391 B)
│
├── 🚀 deploy/                          (scripts déploiement)
│   ├── vps1-mailwizz/                  (install MailWizz)
│   ├── vps2-pmta/                      (install PowerMTA)
│   └── local-api/                      (run API local)
│
├── 📊 monitoring/                      (Prometheus + Grafana)
└── 💾 data/                            (volumes persistants)
```

---

## 🚀 DÉMARRAGE RAPIDE

### Option A : Développement Local (API uniquement)

```bash
cd C:\Users\willi\Documents\Projets\VS_CODE\email-engine

# 1. Fix le crash Pydantic actuel
nano app/config.py
# Ajouter : model_config = SettingsConfigDict(extra='allow')

# 2. Ajouter API_KEY
echo 'API_KEY=dev_key_secure_2026' >> .env

# 3. Démarrer
docker-compose up -d

# 4. Vérifier
curl http://localhost:8000/health
```

### Option B : Production Multi-Serveurs

Voir **README-DEPLOYMENT.md** pour le guide complet.

---

## 📊 COMPARAISON BACKUP-COLD vs EMAIL-ENGINE V2

### Ce qui est PAREIL (hérité de backup-cold)

✅ **MailWizz complet** :
- 106 templates HTML (identiques)
- 77 campagnes autoresponder (identiques)
- Base MySQL (même structure)
- Interface web (même UI)
- API REST (même endpoints)

✅ **PowerMTA** :
- Config de base (Virtual MTAs, DKIM)
- Licence (même fichier)
- Bounce handling
- Queue management

### Ce qui est DIFFÉRENT (amélioré V2)

⭐ **Architecture** :
- V1 : 1 serveur monolithe
- V2 : 2-3 serveurs séparés

⭐ **Scalabilité** :
- V1 : 2 IPs max confortable
- V2 : 5 IPs actuellement → 100+ possible

⭐ **Orchestration** :
- V1 : Scripts manuels
- V2 : API FastAPI automatique

⭐ **Monitoring** :
- V1 : Logs fichiers
- V2 : Prometheus + Grafana + Telegram alerts

⭐ **Warmup** :
- V1 : Manuel (Excel, MailWizz quotas)
- V2 : Automatique (6 semaines intelligent)

⭐ **Multi-tenant** :
- V1 : Single tenant
- V2 : Multi-tenant (Client 1 + Client 2 isolés)

---

## 🔗 COMMUNICATION ENTRE SERVEURS

### VPS1 (MailWizz) ↔ VPS2 (PowerMTA)

```
MailWizz (PHP)
  ↓ SMTP relay localhost:2525
PowerMTA (C++)
  ↓ SMTP :25
Internet
```

**Type** : SMTP direct (MailWizz envoie à PowerMTA)

### Email-Engine ↔ VPS1 (MailWizz)

```python
# Email-Engine appelle API MailWizz
import requests

response = requests.post(
    "https://sos-holidays.com/api/lists/abc123/subscribers",
    headers={"X-API-KEY": "xxx"},
    json={"EMAIL": "john@example.com", "FNAME": "John"}
)
```

**Type** : API HTTP REST

### Email-Engine ↔ VPS2 (PowerMTA)

```python
# Email-Engine génère config PowerMTA
import paramiko

# 1. Générer config
config = generate_pmta_config(ips=5)

# 2. SSH upload
ssh = paramiko.SSHClient()
ssh.connect(vps2_host, username='root', key_filename='ssh_key')
sftp = ssh.open_sftp()
sftp.put('config', '/etc/pmta/config')

# 3. Reload
ssh.exec_command('systemctl reload pmta')
```

**Type** : SSH + fichiers config

---

## ✅ STATUT DU PROJET

### ✅ FAIT (Phase 1)

- [x] API Email-Engine (FastAPI)
- [x] PostgreSQL (5 IPs configurées)
- [x] Redis + Celery
- [x] Monitoring (Prometheus + Grafana)
- [x] Backup-cold copié dans `backup-source/`
- [x] Structure dossiers créée (`deploy/`, `monitoring/`, `data/`)
- [x] Documentation complète (3 README + 1 ARCHITECTURE)

### 🔴 BLOQUÉ ACTUELLEMENT

- [ ] **Fix crash API** : app/config.py Pydantic error (5 min)
- [ ] **Ajouter API_KEY** : .env manquante (1 min)

### 🟡 EN COURS (Phase 2)

- [ ] Extraction MailWizz de backup-source (10 min)
- [ ] Extraction PowerMTA config de backup-source (5 min)
- [ ] Scripts déploiement VPS1 (30 min)
- [ ] Scripts déploiement VPS2 (30 min)

### 🔜 À FAIRE (Phase 3)

- [ ] Déployer VPS1 (MailWizz sur sos-holidays.com)
- [ ] Déployer VPS2 (PowerMTA 5 IPs)
- [ ] Configurer DNS (5 domaines : SPF/DKIM/DMARC/PTR)
- [ ] Tests E2E (Email-Engine → MailWizz → PowerMTA → Gmail)
- [ ] Migration API v2 templates/campaigns

---

## 🚨 ACTION IMMÉDIATE

### Fix crash Email-Engine (URGENT)

Le système VPS Hetzner crashe actuellement avec erreur Pydantic.

**Solution 5 minutes** :

```bash
# Se connecter VPS Hetzner
ssh root@89.167.26.169

# Fix Pydantic
cd /opt/email-engine
nano app/config.py

# Ajouter en ligne 2 de la classe Settings :
model_config = SettingsConfigDict(extra='allow')

# Ajouter API_KEY
echo 'API_KEY=email_engine_prod_key_2026' >> .env

# Redémarrer
docker-compose restart api
sleep 5
curl http://localhost:8000/health
```

---

## 📞 SUPPORT

**Documentation** :
- README.md (API technique)
- README-V2-MULTI-SERVERS.md (ce fichier)
- README-DEPLOYMENT.md (guide déploiement)
- ARCHITECTURE-PRODUCTION.md (détails infrastructure)

**Monitoring** : http://monitoring.domain.com:3000

---

## 📜 LICENCE

Propriétaire - Tous droits réservés

---

**Créé le** : 16 février 2026
**Version** : 2.0.0
**Auteur** : William + Claude Code
**Statut** : 🟡 En développement (Phase 1 complète, Phase 2 en cours)
