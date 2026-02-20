# 🎯 CLARIFICATION ARCHITECTURE FINALE - Email-Engine

**Date** : 16 février 2026 22:30
**Statut** : ✅ Architecture corrigée

---

## 📦 CE QUI A ÉTÉ COPIÉ

### backup-cold → mailwizz-email-engine (223 MB)

```bash
✅ Copié : cp -r "backup-cold" "email-engine/mailwizz-email-engine"

email-engine/
└── mailwizz-email-engine/           # ← Copie complète backup-cold
    ├── mailwizz-prod-20260216.tar.gz    (111 MB)  ← Application MailWizz
    ├── mailapp-prod-20260216.sql.gz     (810 KB)  ← Base de données
    ├── pmta-license-20260216            (391 B)   ← Licence PowerMTA
    ├── pmta-config-20260216             (8.9 KB)  ← Config PowerMTA
    ├── backup-hetzner-20260216.tar.gz   (111 MB)  ← Backup complet
    └── var/                                        ← Extraction
```

---

## 🔄 CE QUI EST UTILISÉ

### ✅ Utilisé depuis mailwizz-email-engine

```
✅ mailwizz-prod-20260216.tar.gz
   → Extraire APPLICATION MailWizz sur VPS1
   → Installer fichiers PHP/CSS/JS

✅ pmta-license-20260216
   → Copier vers /etc/pmta/license sur VPS2
   → Licence perpétuelle réutilisée

✅ pmta-config-20260216 (IMPORTANT !)
   → Config COMPLÈTE de backup-cold réutilisée
   → Garde TOUTES les règles ISP (hotmail, yahoo, gmail, etc.)
   → Garde TOUS les backoff patterns
   → Garde TOUTES les bounce categories
   → Juste ADAPTER : IPs (2→5) + domaines + virtual-mta
```

### ❌ NON utilisé (reste dans mailwizz-email-engine)

```
❌ mailapp-prod-20260216.sql.gz
   → NE PAS importer dans base MySQL
   → Contient : 106 templates, 77 campagnes, segments
   → Raison : Système Email-Engine démarre VIDE

❌ backup-hetzner-20260216.tar.gz
   → Archive complète (référence seulement)

❌ var/
   → Dossier extraction (pas nécessaire)
```

---

## 🏗️ INSTALLATION FINALE

### VPS 1 : MailWizz

```bash
# 1. Upload application MailWizz
scp mailwizz-email-engine/mailwizz-prod-20260216.tar.gz root@VPS1:/tmp/

# 2. Créer base MySQL VIDE
mysql -e "CREATE DATABASE mailwizz_v2"
# ❌ PAS d'import mailapp-prod-20260216.sql.gz

# 3. Extraire application
cd /var/www/html
tar -xzf /tmp/mailwizz-prod-20260216.tar.gz --strip-components=3

# 4. Wizard MailWizz
# → Ouvrir https://sos-holidays.com/install
# → Base VIDE (structure créée par wizard)
# → 0 templates, 0 campagnes
```

**Résultat** :
- ✅ Application MailWizz identique à backup-cold
- ✅ Base de données VIDE (pas de templates/campagnes)
- ✅ Système neuf, prêt pour Email-Engine API

---

### VPS 2 : PowerMTA

```bash
# 1. Upload licence
scp mailwizz-email-engine/pmta-license-20260216 root@VPS2:/tmp/pmta-license

# 2. Copier licence
cp /tmp/pmta-license /etc/pmta/license

# 3. Créer config NOUVELLE (5 IPs)
# → Inspirée de pmta-config-20260216
# → MAIS : 5 IPs au lieu de 2
# → Pattern-list : 1 email par IP

cat > /etc/pmta/config <<EOF
# [Config 5 IPs avec isolation]
EOF

# 4. Générer 5 clés DKIM (neuves)
for i in {1..5}; do
  openssl genrsa -out /etc/pmta/dkim/mail${i}.pem 2048
done
```

**Résultat** :
- ✅ Licence PowerMTA identique à backup-cold
- ✅ Config COMPLÈTE de backup-cold réutilisée (toutes les règles)
- ✅ Config ADAPTÉE pour 5 IPs + nouveaux domaines
- ✅ Clés DKIM neuves (pas réutilisation backup-cold)

**Avantages de réutiliser pmta-config-20260216** :
```
✅ Règles ISP optimisées (Hotmail, Yahoo, Gmail, AOL, Orange, Free, SFR)
   → max-msg-rate par provider
   → max-smtp-out par provider
   → Configurations testées et validées

✅ Backoff patterns (~50 règles)
   → "421 Service not available" → backoff
   → "exceeded the rate limit" → backoff
   → "too many connections" → backoff
   → Protection auto contre blacklisting

✅ Bounce categorization
   → spam-related, virus-related, quota-issues
   → invalid-sender, bad-mailbox, bad-domain
   → policy-related, routing-errors
   → Permet gestion intelligente des bounces

✅ Settings globaux éprouvés
   → retry-after 10m
   → bounce-after 24h
   → use-starttls yes
   → dkim-sign yes
```

---

## 📊 COMPARAISON

| Aspect | backup-cold (origine) | mailwizz-email-engine (copie) | Email-Engine (système final) |
|--------|----------------------|-------------------------------|------------------------------|
| **Location** | `Outils d'emailing/backup-cold/` | `email-engine/mailwizz-email-engine/` | 3 VPS (VPS1 + VPS2 + VPS3) |
| **Fichiers** | 223 MB (originaux) | 223 MB (copie) | Applications installées |
| **MailWizz app** | tar.gz | tar.gz (même fichier) | Extrait sur VPS1 |
| **Base MySQL** | SQL.gz (106 templates) | SQL.gz (PAS UTILISÉ) | Base VIDE (0 templates) |
| **PowerMTA licence** | pmta-license | pmta-license (copié) | Installé sur VPS2 |
| **PowerMTA config** | 2 IPs | 2 IPs (référence) | 5 IPs (nouvelle config) |
| **Statut** | Archive (ne pas toucher) | Référence (ne pas modifier) | Production (actif) |

---

## ✅ RÉSUMÉ

### Ce qu'on a fait

```
1. ✅ Copier backup-cold COMPLET → email-engine/mailwizz-email-engine/
2. ✅ Modifier scripts pour utiliser ces fichiers
3. ✅ MAIS ne PAS importer templates/segments/campagnes
```

### Pourquoi cette approche ?

```
✅ Réutiliser application MailWizz testée (backup-cold)
✅ Réutiliser licence PowerMTA perpétuelle
✅ Réutiliser structure config PowerMTA

❌ NE PAS réutiliser données (templates/campagnes)
   → Email-Engine démarre vierge
   → Templates créés via API
   → Multi-tenant (client-1, backlink-engine, telegram-engine)
```

### Différence avec backup-cold

| backup-cold | Email-Engine |
|-------------|--------------|
| 2 IPs | **5 IPs** (scalable 100+) |
| 2 domaines | **5 domaines** |
| 106 templates | **0 templates** (créés via API) |
| 77 campagnes | **0 campagnes** (créées via API) |
| Mono-tenant | **Multi-tenant** |
| Pas d'API | **API REST FastAPI** |
| Pas de monitoring | **Prometheus + Grafana** |
| Manuel | **Automatisé** (warmup, bounce, retry) |

---

## 🚀 COMMANDES FINALES

### 1. Vérifier copie

```bash
cd email-engine
ls -lh mailwizz-email-engine/

# Doit afficher :
# mailwizz-prod-20260216.tar.gz  (111 MB)
# pmta-license-20260216          (391 B)
# mailapp-prod-20260216.sql.gz   (810 KB) ← PAS UTILISÉ
```

### 2. Déployer

```bash
cd deploy

# Éditer IPs
nano deploy-all.sh
# → VPS1_IP, VPS2_IP, VPS3_IP

# Éditer .env.production
cd ..
cp .env.production.example .env.production
nano .env.production
# → Remplir IPs, passwords, etc.

# Lancer déploiement
cd deploy
./deploy-all.sh
```

### 3. Résultat attendu

```
VPS1 : MailWizz installé (app de backup-cold, base VIDE)
VPS2 : PowerMTA installé (licence de backup-cold, config 5 IPs)
VPS3 : Email-Engine API opérationnel

Base MySQL : VIDE (structure MailWizz, 0 templates)
Templates : Créés via API Email-Engine
Campagnes : Créées via API Email-Engine
```

---

## 🎯 CONCLUSION

```
backup-cold (V1)                 Email-Engine (V2)
────────────────                 ─────────────────
Archive complète                 Système nouveau
Ne pas toucher                   Production active

Lien :
└─ Copie dans mailwizz-email-engine/
   ├─ ✅ Application MailWizz réutilisée
   ├─ ✅ Licence PowerMTA réutilisée
   └─ ❌ Données (templates/campagnes) NON réutilisées
```

**Architecture finale** : ✅ Validée
**Prochaine étape** : Déploiement sur VPS

---

**Document créé le** : 16 février 2026 22:30
**Statut** : ✅ Architecture clarifiée et corrigée
