# ✅ Configuration Finale - Email-Engine (Option 2)

**Date** : 2026-02-16
**Status** : ✅ Licence PMTA installée - Clés MailWizz à configurer

---

## 🎉 CE QUI EST DÉJÀ FAIT

### ✅ Licence PowerMTA

```
✅ Licence copiée : email-engine/powermta/license
✅ Docker configuré : Monte vers /etc/pmta/license (MÊME CHEMIN que Système 1)
✅ Code lit depuis : /etc/pmta/config (variable PMTA_CONFIG_PATH dans .env)
```

**Vérification** :
```bash
cd email-engine
cat powermta/license
```

Vous devriez voir :
```
product: PowerMTA
version: 5.0
licensee: softomaniac
expires: never
```

✅ **Parfait ! C'est la même licence que Système 1**

---

## ⏳ CE QU'IL RESTE À FAIRE

### 📝 Configurer les Clés MailWizz dans .env

**Fichier** : `email-engine/.env`

Vous devez éditer ces 4 lignes avec vos vraies clés :

```env
# Ligne 55 : Clé publique générale
MAILWIZZ_API_PUBLIC_KEY=VOTRE_CLE_PUBLIQUE_ICI

# Ligne 56 : Clé privée générale
MAILWIZZ_API_PRIVATE_KEY=VOTRE_CLE_PRIVEE_ICI

# Ligne 70 : Clé API SOS-Expat
MAILWIZZ_SOS_API_KEY=VOTRE_CLE_SOS_EXPAT_ICI

# Ligne 75 : Clé API Ulixai
MAILWIZZ_ULIXAI_API_KEY=VOTRE_CLE_ULIXAI_ICI
```

---

## 🔍 COMMENT RÉCUPÉRER VOS CLÉS MAILWIZZ

### Option A : Depuis le Système 1 (serveur Hetzner)

**Via SSH** :

```bash
# Se connecter au serveur
ssh root@46.62.168.55

# Accéder à la base MySQL
mysql -u mailapp -p mailapp
# Mot de passe : WJullin1974/*%$

# Lister les clés API
SELECT customer_id, public, private, date_added
FROM mw_customer_api_key
WHERE is_active = 1;
```

**Résultat** :
```
| customer_id | public                           | private                          |
|-------------|----------------------------------|----------------------------------|
| 1           | abc123...                        | xyz789...                        |
| 2           | def456...                        | uvw012...                        |
```

Copiez ces valeurs dans votre `.env`

---

### Option B : Via l'interface web MailWizz

1. **Se connecter** :
   - SOS-Expat : https://mail.sos-expat.com/backend
   - Ulixai : https://mail.ulixai.com/backend

2. **Menu** : Settings → API Keys

3. **Copier** :
   - Public Key → `MAILWIZZ_API_PUBLIC_KEY`
   - Private Key → `MAILWIZZ_API_PRIVATE_KEY`

---

### Option C : Depuis le backup local

**Extraire depuis la base SQL** :

```powershell
cd "C:\Users\willi\Documents\Projets\VS_CODE\sos-expat-project\Outils d'emailing\backup-cold"

# Décompresser et chercher les clés
zcat mailapp-prod-20260216.sql.gz | grep -A 2 "INSERT INTO \`mw_customer_api_key\`"
```

---

## 🚀 DÉMARRAGE RAPIDE

### 1. Éditer le .env

```powershell
cd C:\Users\willi\Documents\Projets\VS_CODE\email-engine
notepad .env
```

**Chercher et modifier** :
- Ligne 55 : `MAILWIZZ_API_PUBLIC_KEY=`
- Ligne 56 : `MAILWIZZ_API_PRIVATE_KEY=`
- Ligne 70 : `MAILWIZZ_SOS_API_KEY=`
- Ligne 75 : `MAILWIZZ_ULIXAI_API_KEY=`

### 2. Enregistrer et fermer

### 3. Démarrer email-engine

```powershell
cd C:\Users\willi\Documents\Projets\VS_CODE\email-engine

# Démarrer tous les services
docker-compose up -d

# Voir les logs
docker-compose logs -f api
```

### 4. Vérifier

```powershell
# Health check
curl http://localhost:8000/health

# Documentation API
# Ouvrir dans le navigateur : http://localhost:8000/docs
```

---

## 📊 COMPARAISON : Système 1 vs Système 2 (Configuré)

| Élément | Système 1 (MailWizz+PMTA) | Système 2 (Email-Engine) |
|---------|---------------------------|--------------------------|
| **Licence PMTA** | `/etc/pmta/license` | `/etc/pmta/license` ✅ IDENTIQUE |
| **Config PMTA** | `/etc/pmta/config` | `/etc/pmta/config` ✅ IDENTIQUE |
| **Clés MailWizz** | MySQL `mw_customer_api_key` | `.env` (temporaire) |
| **Stockage** | Serveur Hetzner | Docker local |

---

## ✅ CHECKLIST

- [x] Licence PMTA copiée dans `powermta/license`
- [x] Docker-compose configuré (mount vers `/etc/pmta/license`)
- [x] Fichier `.env` créé
- [ ] **Clés MailWizz ajoutées dans `.env`** ← À FAIRE
- [ ] Docker démarré (`docker-compose up -d`)
- [ ] API accessible (`http://localhost:8000/health`)

---

## 🎯 PROCHAINE ÉTAPE

**Maintenant** : Récupérez vos clés MailWizz et mettez-les dans `.env`

**Ensuite** : Démarrez email-engine avec `docker-compose up -d`

**Questions** : Consultez `QUICKSTART.md` pour plus d'aide

---

## 🔐 SÉCURITÉ

**Important** :
- ✅ Fichier `.env` est dans `.gitignore` (vos clés ne seront pas commitées)
- ✅ Licence PMTA en lecture seule (`:ro` dans docker-compose.yml)
- ⚠️  Ne partagez jamais vos clés MailWizz
- ⚠️  Changez les mots de passe par défaut dans `.env`

---

**Configuration créée le** : 2026-02-16 13:30
**Status** : ✅ 80% terminé - Il ne reste que les clés MailWizz à configurer
