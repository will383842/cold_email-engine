# 🔐 Option Alternative : Stocker les Licences comme Système 1

**Objectif** : Stocker les licences PMTA et clés MailWizz de la même façon que le système MailWizz+PMTA Hetzner (dans la base de données et fichiers système)

---

## 📊 COMPARAISON

### Méthode Actuelle (fichier .env)

```
email-engine/
├─ .env                          ← Clés MailWizz en variables
├─ powermta/license              ← Licence PMTA
└─ powermta/config               ← Config PMTA
```

**✅ Avantages** :
- Simple et rapide
- Tout centralisé dans `.env`
- Facile à déployer avec Docker

**❌ Inconvénients** :
- Différent du système 1
- Fichier `.env` à protéger

---

### Méthode Système 1 (base de données)

```
Serveur:
├─ /etc/pmta/license             ← Licence PMTA (fichier système)
├─ /etc/pmta/config              ← Config PMTA (fichier système)
└─ Base PostgreSQL
   └─ Table api_keys             ← Clés MailWizz (en BDD)
```

**✅ Avantages** :
- Identique au système 1
- Clés gérées via API/UI
- Plus sécurisé (pas de fichier texte)

**❌ Inconvénients** :
- Plus complexe à mettre en place
- Nécessite création de tables et API

---

## 🎯 SOLUTION : Hybride (Recommandé)

### Option A : Garder .env MAIS monter les fichiers comme Système 1

```yaml
# docker-compose.yml
services:
  api:
    volumes:
      # Monter la licence PMTA au même endroit que Système 1
      - ./powermta/license:/etc/pmta/license:ro
      - ./powermta/config:/etc/pmta/config:ro
```

**Code application lit depuis** : `/etc/pmta/license` (comme Système 1)

✅ **Avantage** : Chemins identiques aux 2 systèmes

---

### Option B : Stocker clés MailWizz dans PostgreSQL

#### 1. Créer la table (comme MySQL `mw_customer_api_key`)

```sql
-- Migration: create_api_keys_table.sql
CREATE TABLE api_keys (
    key_id SERIAL PRIMARY KEY,
    tenant_id INT NOT NULL REFERENCES tenants(id),
    public_key VARCHAR(64) NOT NULL UNIQUE,
    private_key VARCHAR(64) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index
CREATE INDEX idx_api_keys_tenant ON api_keys(tenant_id);
CREATE INDEX idx_api_keys_public ON api_keys(public_key);
```

#### 2. Peupler avec vos clés actuelles

```sql
-- Insérer les clés de vos licences MailWizz
INSERT INTO api_keys (tenant_id, public_key, private_key)
VALUES
  (1, 'votre_cle_publique_sos_expat', 'votre_cle_privee_sos_expat'),
  (2, 'votre_cle_publique_client2', 'votre_cle_privee_client2');
```

#### 3. Modifier le code pour lire depuis PostgreSQL

**Fichier** : `src/infrastructure/mailwizz/client.py`

```python
# AVANT (lit depuis .env)
api_key = os.getenv("MAILWIZZ_SOS_API_KEY")

# APRÈS (lit depuis PostgreSQL)
def get_api_keys(tenant_id: int) -> dict:
    """Récupère les clés API depuis PostgreSQL (comme Système 1)"""
    query = """
        SELECT public_key, private_key
        FROM api_keys
        WHERE tenant_id = %s AND is_active = true
        LIMIT 1
    """
    result = db.execute(query, (tenant_id,))
    return result[0] if result else None
```

---

## 🚀 MISE EN PLACE : Méthode Système 1

### Étape 1 : Créer la table api_keys

```bash
cd email-engine

# Créer la migration
docker-compose exec api alembic revision -m "create_api_keys_table"
```

**Fichier généré** : `alembic/versions/XXXX_create_api_keys_table.py`

```python
"""create api_keys table"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        'api_keys',
        sa.Column('key_id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('public_key', sa.String(64), nullable=False),
        sa.Column('private_key', sa.String(64), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('key_id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
    )
    op.create_index('idx_api_keys_tenant', 'api_keys', ['tenant_id'])
    op.create_index('idx_api_keys_public', 'api_keys', ['public_key'], unique=True)

def downgrade():
    op.drop_index('idx_api_keys_public')
    op.drop_index('idx_api_keys_tenant')
    op.drop_table('api_keys')
```

### Étape 2 : Appliquer la migration

```bash
docker-compose exec api alembic upgrade head
```

### Étape 3 : Insérer vos clés MailWizz

```bash
docker-compose exec postgres psql -U email_engine -d email_engine
```

```sql
-- Remplacer par vos vraies clés
INSERT INTO api_keys (tenant_id, public_key, private_key)
VALUES
  (1, 'cle_publique_sos_expat_ici', 'cle_privee_sos_expat_ici'),
  (2, 'cle_publique_client2_ici', 'cle_privee_client2_ici');

-- Vérifier
SELECT * FROM api_keys;
```

### Étape 4 : Modifier le code (optionnel)

Si vous voulez lire depuis la BDD au lieu de `.env`, modifiez :

**`src/infrastructure/mailwizz/repository.py`**

```python
class MailWizzRepository:
    def __init__(self, db: Database):
        self.db = db

    def get_api_credentials(self, tenant_id: int) -> Optional[dict]:
        """Récupère les credentials API depuis PostgreSQL (comme mw_customer_api_key)"""
        query = """
            SELECT public_key, private_key
            FROM api_keys
            WHERE tenant_id = :tenant_id AND is_active = true
            LIMIT 1
        """
        result = self.db.fetch_one(query, {"tenant_id": tenant_id})
        return result if result else None
```

---

## 📋 RÉCAPITULATIF : Les 3 Options

| Option | Licence PMTA | Clés MailWizz | Avantage |
|--------|--------------|---------------|----------|
| **Option 1** (actuel) | `powermta/license` | `.env` | ✅ Simple, rapide |
| **Option 2** (hybride) | `/etc/pmta/license` | `.env` | ✅ Chemin PMTA comme Système 1 |
| **Option 3** (identique S1) | `/etc/pmta/license` | PostgreSQL `api_keys` | ✅ 100% comme Système 1 |

---

## 🎯 RECOMMANDATION

### Pour débuter (maintenant) :

**Option 2 (Hybride)** : Mettre licence PMTA dans `/etc/pmta/license`, garder clés dans `.env`

```bash
# 1. Copier la licence au bon endroit
mkdir -p powermta
cp ../Outils\ d\'emailing/backup-cold/pmta-license-20260216 powermta/license

# 2. Modifier docker-compose.yml
# (mount vers /etc/pmta/license)

# 3. Éditer .env avec vos clés MailWizz
nano .env
```

### Pour production (plus tard) :

**Option 3 (Identique S1)** : Stocker clés MailWizz dans PostgreSQL

- Créer table `api_keys`
- Insérer vos clés
- Modifier le code pour lire depuis BDD
- Avantage : Interface d'administration possible

---

## ❓ QUELLE OPTION CHOISIR ?

**Vous voulez** : Faire exactement comme Système 1 ?
→ **Option 3** : Créer table `api_keys` dans PostgreSQL

**Vous voulez** : Démarrer rapidement ?
→ **Option 2** : Licence PMTA dans `/etc/pmta/license`, clés dans `.env`

**Vous voulez** : Ultra simple ?
→ **Option 1** : Tout dans `.env` (méthode actuelle)

---

## 🚀 DÉMARRAGE RAPIDE (Option 2 - Recommandé)

```powershell
cd C:\Users\willi\Documents\Projets\VS_CODE\email-engine

# 1. Copier licence PMTA depuis Système 1
Copy-Item "..\Outils d'emailing\backup-cold\pmta-license-20260216" "powermta\license"

# 2. Éditer .env avec vos clés MailWizz
notepad .env

# 3. Démarrer
docker-compose up -d
```

✅ **Vous aurez** : Licence PMTA au même endroit que Système 1, clés MailWizz dans `.env` (pour l'instant)

---

**Voulez-vous que je mette en place l'Option 3 (table PostgreSQL) ?** 🤔
