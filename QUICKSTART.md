# Email Engine - Guide de Démarrage Rapide

Ce guide vous permet de démarrer l'Email Engine en moins de 5 minutes.

---

## Prérequis

- Docker & Docker Compose installés
- Git (optionnel)
- Minimum 4GB RAM disponible
- Ports libres: 8000, 5432, 6379, 5555

---

## Démarrage en 5 Minutes

### 1. Configuration

```bash
# Copier le fichier d'environnement
cp .env.example .env

# Éditer .env avec vos valeurs (minimum requis ci-dessous)
```

**Variables minimales requises**:
```env
# Database
DATABASE_URL=postgresql://email_engine:email_engine_password@postgres:5432/email_engine

# Redis
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# API Keys (utilisez ces valeurs par défaut pour commencer)
API_KEY_SOS_EXPAT=sos-expat-internal-key-2026
API_KEY_ULIXAI=ulixai-internal-key-2026
API_KEY_ADMIN=admin-master-key-2026
```

### 2. Lancer les Services

```bash
# Démarrer tous les services Docker
docker-compose up -d

# Vérifier que tous les services sont démarrés
docker-compose ps
```

Vous devriez voir 9 services en état "Up":
- postgres
- redis
- api
- celery_validation
- celery_mailwizz
- celery_campaigns
- celery_warmup
- celery_beat
- flower

### 3. Initialiser la Base de Données

```bash
# Créer les tables
docker-compose exec api alembic upgrade head

# Peupler avec des données de test
docker-compose exec api python scripts/seed_enterprise_data.py
```

### 4. Vérifier l'Installation

Ouvrez votre navigateur:

- **API Documentation**: http://localhost:8000/docs
- **Alternative (ReDoc)**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health
- **Celery Monitor**: http://localhost:5555

---

## Premiers Tests

### 1. Vérifier les Tenants

```bash
curl http://localhost:8000/api/v2/stats/1/overview
curl http://localhost:8000/api/v2/stats/2/overview
```

### 2. Lister les Contacts

```bash
# SOS-Expat (tenant 1)
curl http://localhost:8000/api/v2/contacts/1

# Ulixai (tenant 2)
curl http://localhost:8000/api/v2/contacts/2
```

### 3. Créer une Campagne

```bash
curl -X POST http://localhost:8000/api/v2/campaigns \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": 1,
    "name": "Test Campaign",
    "language": "fr"
  }'
```

### 4. Voir les Tags

```bash
curl http://localhost:8000/api/v2/tags/1
```

---

## Structure des Données Créées

Après `seed_enterprise_data.py`:

### Tenants
- **Tenant 1**: SOS-Expat (id=1)
- **Tenant 2**: Ulixai (id=2)

### IPs
- **SOS-Expat**: 50 IPs (45.123.10.1-50)
- **Ulixai**: 50 IPs (45.124.20.1-50)

### Domaines
- **SOS-Expat**: mail1-50.sos-mail.com
- **Ulixai**: mail1-50.ulixai-mail.com

### Tags (16 tags par tenant)
- verified, active, inactive, high_value, real_estate
- technology, healthcare, finance, retail, education
- france, belgium, switzerland, canada, unsubscribed, bounced

### MailWizz Instances
- **SOS-Expat**: mail.sos-expat.com
- **Ulixai**: mail.ulixai.com

---

## Commandes Utiles

### Voir les Logs

```bash
# Tous les services
docker-compose logs -f

# Service spécifique
docker-compose logs -f api
docker-compose logs -f celery_campaigns

# Dernières 100 lignes
docker-compose logs --tail=100 api
```

### Redémarrer un Service

```bash
# API seulement
docker-compose restart api

# Tous les workers Celery
docker-compose restart celery_validation celery_mailwizz celery_campaigns celery_warmup
```

### Accéder à un Container

```bash
# Shell dans l'API
docker-compose exec api bash

# Shell PostgreSQL
docker-compose exec postgres psql -U email_engine

# Redis CLI
docker-compose exec redis redis-cli
```

### Arrêter les Services

```bash
# Arrêter sans supprimer les données
docker-compose stop

# Arrêter et supprimer les containers
docker-compose down

# Arrêter et supprimer TOUT (containers + volumes)
docker-compose down -v
```

---

## Endpoints Principaux

### API v1 (Legacy)
- `/api/v1/ips` - Gestion des IPs
- `/api/v1/domains` - Gestion des domaines
- `/api/v1/warmup` - Warmup des IPs
- `/api/v1/blacklists` - Vérification blacklists

### API v2 (Clean Architecture)
- `/api/v2/contacts` - Gestion des contacts
- `/api/v2/campaigns` - Gestion des campagnes
- `/api/v2/templates` - Templates d'email
- `/api/v2/tags` - Gestion des tags
- `/api/v2/data-sources` - Sources de données
- `/api/v2/stats` - Statistiques & métriques
- `/api/v2/webhooks` - Webhooks externes

---

## Monitoring

### Celery Flower
Ouvrez http://localhost:5555 pour voir:
- Workers actifs
- Tâches en cours
- Longueur des queues
- Taux de succès/échec
- Utilisation des ressources

### Health Checks

```bash
# API
curl http://localhost:8000/health

# Database
docker-compose exec postgres pg_isready

# Redis
docker-compose exec redis redis-cli ping

# Celery workers (via Flower)
curl http://localhost:5555/api/workers
```

---

## Dépannage

### Le port 8000 est déjà utilisé

```bash
# Dans .env, changer:
API_PORT=8001

# Puis dans docker-compose.yml:
ports:
  - "8001:8000"
```

### Erreur de connexion à la base de données

```bash
# Vérifier que PostgreSQL est démarré
docker-compose ps postgres

# Voir les logs
docker-compose logs postgres

# Recréer le container
docker-compose down
docker-compose up -d postgres
```

### Celery workers ne démarrent pas

```bash
# Vérifier Redis
docker-compose logs redis

# Redémarrer les workers
docker-compose restart celery_validation celery_mailwizz celery_campaigns celery_warmup
```

### Réinitialiser complètement

```bash
# ATTENTION: Cela supprime TOUTES les données!
docker-compose down -v
docker-compose up -d
docker-compose exec api alembic upgrade head
docker-compose exec api python scripts/seed_enterprise_data.py
```

---

## Prochaines Étapes

Maintenant que votre environnement est configuré:

1. **Explorez l'API**: http://localhost:8000/docs
2. **Lisez la documentation complète**: `docs/IMPLEMENTATION_SUMMARY.md`
3. **Consultez les exemples**: `docs/PHASE3_COMPLETION.md`
4. **Configurez vos intégrations**:
   - MailWizz API keys
   - PowerMTA configuration
   - Scraper-Pro API
   - Backlink Engine API

---

## Support

- **Documentation interactive**: http://localhost:8000/docs
- **Logs en temps réel**: `docker-compose logs -f api`
- **Monitoring Celery**: http://localhost:5555
- **Health check**: `curl http://localhost:8000/health`

---

**Bon travail avec Email Engine! 🚀**

Pour une documentation complète, consultez:
- `docs/IMPLEMENTATION_SUMMARY.md` - Vue d'ensemble complète
- `docs/PHASE3_COMPLETION.md` - Détails de la Phase 3
- `docs/ARCHITECTURE.md` - Architecture Clean/Hexagonal
