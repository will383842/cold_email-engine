# Corrections du Warmup - Production Ready ✅

Date: 2026-02-16
Durée: ~3 heures de travail
Status: **TERMINÉ - PRODUCTION READY**

---

## Problèmes Identifiés et Corrigés

### ❌ PROBLÈME 1: WarmupEngine non utilisé

**Symptôme**: La tâche `advance_warmup_task` avait une logique simplifiée avec "TODO" dans le code

**Impact**: Le warmup professionnel (`WarmupEngine`) existait mais n'était jamais appelé

**Correction**: ✅ `src/infrastructure/background/tasks.py`

```python
# AVANT (simplifié)
def advance_warmup_task():
    # TODO: Implement proper advancement logic from warmup_engine service
    # Simple advancement: double quota if < target
    new_quota = min(current_quota * 2, warmup_plan.target_daily_quota)

# APRÈS (professionnel)
def advance_warmup_task():
    import asyncio
    from app.services.warmup_engine import WarmupEngine

    engine = WarmupEngine(db)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(engine.daily_tick())
```

**Bénéfices**:
- ✅ Utilise maintenant le `WarmupEngine` complet
- ✅ Vérifie les taux de bounce (< 5%)
- ✅ Vérifie les taux de spam (< 0.1%)
- ✅ Pause automatique si problème
- ✅ Alertes Telegram
- ✅ Avancement automatique après 7 jours

---

### ❌ PROBLÈME 2: Stats quotidiennes non enregistrées

**Symptôme**: Pas de consolidation des stats Redis → PostgreSQL

**Impact**: Impossible de tracker la progression du warmup

**Correction**: ✅ Nouvelle tâche `consolidate_warmup_stats_task`

```python
@celery_app.task
def consolidate_warmup_stats_task() -> dict:
    """
    Consolidate Redis warmup counters to PostgreSQL (runs daily at 00:30).

    Flow:
        1. Get all warming IPs from database
        2. For each IP, read yesterday's stats from Redis
        3. Save to WarmupDailyStat table
        4. Delete Redis keys after successful save

    Redis Keys:
        warmup:ip:{ip_id}:date:{YYYY-MM-DD}:sent
        warmup:ip:{ip_id}:date:{YYYY-MM-DD}:delivered
        warmup:ip:{ip_id}:date:{YYYY-MM-DD}:bounced
        warmup:ip:{ip_id}:date:{YYYY-MM-DD}:complaints
        warmup:ip:{ip_id}:date:{YYYY-MM-DD}:opens
        warmup:ip:{ip_id}:date:{YYYY-MM-DD}:clicks
    """
```

**Bénéfices**:
- ✅ Tracking en temps réel via Redis
- ✅ Historique permanent dans PostgreSQL
- ✅ Stats consolidées une fois par jour
- ✅ Nettoyage automatique Redis

**Aussi créé**: `record_warmup_stats_task` pour enregistrement direct (optionnel)

---

### ❌ PROBLÈME 3: Webhooks ne trackent pas les IPs en warmup

**Symptôme**: Événements MailWizz/PowerMTA créés mais pas liés au warmup

**Impact**: Pas de données pour calculer les taux de bounce/spam

**Correction**: ✅ `src/presentation/api/v2/webhooks.py`

**Ajout fonction helper**:

```python
def _track_warmup_event(
    db: Session,
    sending_ip: Optional[str],
    event_type: EventType,
) -> None:
    """
    Track warmup stats for IPs in warming status.

    Increments Redis counters for daily warmup tracking.
    """
    if not sending_ip:
        return

    # Find IP in warming status
    ip = db.query(IP).filter(
        IP.address == sending_ip,
        IP.status == "warming"
    ).first()

    if not ip or not ip.warmup_plan:
        return

    # Increment appropriate counter in Redis
    cache = get_cache()
    today = datetime.utcnow().date().isoformat()
    key_prefix = f"warmup:ip:{ip.id}:date:{today}"

    if event_type == EventType.SENT:
        cache.increment(f"{key_prefix}:sent")
    elif event_type == EventType.DELIVERED:
        cache.increment(f"{key_prefix}:delivered")
    # ... etc
```

**Intégré dans**:
- ✅ `mailwizz_webhook()` - Track MailWizz events
- ✅ `powermta_webhook()` - Track PowerMTA events
- ✅ Ajout `sending_ip` au schéma PowerMTAWebhookRequest

**Bénéfices**:
- ✅ Chaque événement webhook incrémente Redis
- ✅ Tracking automatique pour IPs en warmup
- ✅ Pas d'impact sur IPs actives (skip si pas en warmup)
- ✅ Performance optimale (Redis counters)

---

### ✅ BONUS: Configuration Celery Beat

**Fichier**: `src/infrastructure/background/celery_app.py`

**Corrections**:

```python
from celery.schedules import crontab

# Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    # Consolidate warmup stats from Redis to PostgreSQL
    "consolidate-warmup-stats-daily": {
        "task": "src.infrastructure.background.tasks.consolidate_warmup_stats_task",
        "schedule": crontab(hour=0, minute=30),  # 00:30 UTC every day
    },
    # Advance warmup phases
    "advance-warmup-daily": {
        "task": "src.infrastructure.background.tasks.advance_warmup_task",
        "schedule": crontab(hour=1, minute=0),  # 01:00 UTC every day
    },
}

# Task routing
celery_app.conf.task_routes = {
    "src.infrastructure.background.tasks.consolidate_warmup_stats_task": {"queue": "warmup"},
    # ... existing routes
}
```

**Bénéfices**:
- ✅ Heures précises (crontab) au lieu de 86400 secondes
- ✅ Consolidation à 00:30, avancement à 01:00
- ✅ Route vers queue "warmup" dédiée

---

### ✅ BONUS: Script `add_domain.py`

**Fichier**: `scripts/add_domain.py`

Script complet pour ajouter progressivement des domaines (5 → 50+)

**Usage**:

```bash
# Ajouter 6ème domaine pour SOS-Expat
python scripts/add_domain.py --tenant 1 --domain mail6.sos-mail.com --ip 45.123.10.6

# Dry run (preview)
python scripts/add_domain.py --tenant 1 --domain mail6.sos-mail.com --ip 45.123.10.6 --dry-run
```

**Features**:
- ✅ Validation complète (tenant, domain, IP)
- ✅ Vérification des doublons
- ✅ Création domain + IP + warmup plan
- ✅ Dry-run mode
- ✅ Summary détaillé avec next steps
- ✅ Documentation intégrée
- ✅ Error handling complet

---

## Résumé des Fichiers Modifiés/Créés

### Fichiers Modifiés (3)

1. **src/infrastructure/background/tasks.py**
   - Correction `advance_warmup_task()` → utilise WarmupEngine
   - Ajout `consolidate_warmup_stats_task()`
   - Ajout `record_warmup_stats_task()`
   - +160 lignes

2. **src/infrastructure/background/celery_app.py**
   - Import crontab
   - Configuration beat_schedule améliorée
   - Task routing pour consolidation
   - +10 lignes

3. **src/presentation/api/v2/webhooks.py**
   - Ajout `_track_warmup_event()` helper
   - Intégration dans `mailwizz_webhook()`
   - Intégration dans `powermta_webhook()`
   - Ajout `sending_ip` au schéma PowerMTA
   - +75 lignes

### Fichiers Créés (1)

4. **scripts/add_domain.py**
   - Script complet pour ajout progressif
   - Validation + dry-run mode
   - Documentation intégrée
   - +350 lignes

**Total**: +595 lignes de code production-ready

---

## Flow Complet du Warmup (Production)

### 1. Événements en Temps Réel (Redis)

```
Email envoyé via PowerMTA
    ↓
Événement arrive (webhook)
    ↓
powermta_webhook() appelé
    ↓
_create_contact_event() - Sauvegarde événement
    ↓
_track_warmup_event() - Incrémente Redis si IP en warmup
    ↓
Redis counter: warmup:ip:1:date:2026-02-16:delivered++
```

**Avantages Redis**:
- Performance (incrémentation atomique)
- Pas de load sur PostgreSQL
- Compteurs en temps réel

### 2. Consolidation Quotidienne (PostgreSQL)

```
Celery Beat - 00:30 UTC
    ↓
consolidate_warmup_stats_task()
    ↓
Pour chaque IP en warmup:
  - Lire compteurs Redis (yesterday)
  - Créer WarmupDailyStat en PostgreSQL
  - Supprimer keys Redis
    ↓
Historique permanent dans DB
```

**Avantages PostgreSQL**:
- Historique permanent
- Analyse sur 7 jours
- Calcul des taux (bounce/spam)

### 3. Avancement des Phases (Quotidien)

```
Celery Beat - 01:00 UTC
    ↓
advance_warmup_task()
    ↓
WarmupEngine.daily_tick()
    ↓
Pour chaque warmup plan:
  - Unpause si pause_until dépassé
  - Vérifie stats 7 derniers jours
  - Calcule bounce_rate & spam_rate
  - PAUSE si > seuils
  - ADVANCE si 7 jours OK
  - UPDATE quotas selon phase
  - ACTIVE si completed
    ↓
Alertes Telegram si problème
```

**Critères d'avancement**:
- ✅ 7 jours dans la phase actuelle
- ✅ bounce_rate < 5%
- ✅ spam_rate < 0.1%
- ✅ Pas de pause en cours

---

## Configuration .env Requise

```env
# Warmup Quotas (6 semaines)
WARMUP_WEEK1_QUOTA=50
WARMUP_WEEK2_QUOTA=200
WARMUP_WEEK3_QUOTA=500
WARMUP_WEEK4_QUOTA=1500
WARMUP_WEEK5_QUOTA=5000
WARMUP_WEEK6_QUOTA=10000

# Safety Thresholds
WARMUP_MAX_BOUNCE_RATE=5.0    # Max 5% bounces
WARMUP_MAX_SPAM_RATE=0.1      # Max 0.1% complaints

# Telegram Alerts (IMPORTANT)
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Redis (pour tracking warmup)
REDIS_URL=redis://localhost:6379/0
REDIS_CACHE_DB=1

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

---

## Vérification de l'Installation

### 1. Vérifier que les tâches sont enregistrées

```bash
docker-compose exec api celery -A src.infrastructure.background.celery_app inspect registered
```

**Devrait afficher**:
```
src.infrastructure.background.tasks.advance_warmup_task
src.infrastructure.background.tasks.consolidate_warmup_stats_task
src.infrastructure.background.tasks.record_warmup_stats_task
src.infrastructure.background.tasks.validate_contact_task
src.infrastructure.background.tasks.inject_contact_to_mailwizz_task
src.infrastructure.background.tasks.send_campaign_task
```

### 2. Vérifier le schedule Celery Beat

```bash
docker-compose exec celery_beat celery -A src.infrastructure.background.celery_app inspect scheduled
```

**Devrait afficher**:
```
consolidate-warmup-stats-daily: crontab(0, 30, *, *, *)
advance-warmup-daily: crontab(1, 0, *, *, *)
```

### 3. Test Manuel de consolidation

```bash
# Dans le container API
docker-compose exec api python << EOF
from src.infrastructure.background.tasks import consolidate_warmup_stats_task
result = consolidate_warmup_stats_task()
print(result)
EOF
```

### 4. Test du script add_domain

```bash
# Dry run
docker-compose exec api python scripts/add_domain.py \
  --tenant 1 \
  --domain mail6.sos-mail.com \
  --ip 45.123.10.6 \
  --dry-run

# Vrai ajout
docker-compose exec api python scripts/add_domain.py \
  --tenant 1 \
  --domain mail6.sos-mail.com \
  --ip 45.123.10.6
```

---

## Monitoring du Warmup

### API Endpoints Existants

```bash
# Voir tous les IPs en warmup
curl http://localhost:8000/api/v1/warmup

# Voir un IP spécifique
curl http://localhost:8000/api/v1/ips/1
```

### Redis Keys à Surveiller

```bash
# Voir les compteurs du jour pour IP 1
docker-compose exec redis redis-cli KEYS "warmup:ip:1:date:*"

# Lire un compteur
docker-compose exec redis redis-cli GET "warmup:ip:1:date:2026-02-16:delivered"
```

### PostgreSQL Stats

```sql
-- Stats des 7 derniers jours pour un plan
SELECT date, sent, delivered, bounced, complaints, opens, clicks
FROM warmup_daily_stats
WHERE plan_id = 1
ORDER BY date DESC
LIMIT 7;

-- Taux de bounce/spam pour un plan
SELECT
  SUM(sent) as total_sent,
  SUM(bounced) as total_bounced,
  SUM(complaints) as total_complaints,
  ROUND(SUM(bounced)::numeric / SUM(sent)::numeric * 100, 2) as bounce_rate,
  ROUND(SUM(complaints)::numeric / SUM(sent)::numeric * 100, 4) as spam_rate
FROM warmup_daily_stats
WHERE plan_id = 1
  AND date >= CURRENT_DATE - INTERVAL '7 days';
```

---

## Checklist Déploiement Production

### Avant Premier Envoi

- [ ] Configuration .env complète (quotas, seuils, Telegram)
- [ ] Celery Beat démarré (`docker-compose up celery_beat`)
- [ ] Workers warmup démarrés (`docker-compose up celery_warmup`)
- [ ] Redis fonctionnel (test: `redis-cli PING`)
- [ ] Bot Telegram configuré et testé
- [ ] DNS configurés pour premier domaine
- [ ] PowerMTA VirtualMTA configuré

### Premier Jour

- [ ] Créer premier domaine avec `add_domain.py`
- [ ] Vérifier warmup plan créé (quota=50)
- [ ] Envoyer 50 emails max
- [ ] Vérifier compteurs Redis incrémentés
- [ ] Attendre 24h avant envoi suivant

### Première Semaine

- [ ] Ajouter 1 nouveau domaine tous les 1-2 jours (max 5 total)
- [ ] Surveiller taux bounce < 5%
- [ ] Surveiller taux spam < 0.1%
- [ ] Vérifier alertes Telegram
- [ ] Consolider stats chaque jour

### Après 6 Semaines

- [ ] Premier IP passe en ACTIVE (10,000/jour)
- [ ] Continuer ajout 1 domaine/semaine max
- [ ] Capacité totale = nb_active × 10,000

---

## Support & Dépannage

### Problème: Consolidation ne fonctionne pas

**Vérifier**:
```bash
# Logs Celery Beat
docker-compose logs celery_beat | grep consolidate

# Test manuel
docker-compose exec api python -c "from src.infrastructure.background.tasks import consolidate_warmup_stats_task; print(consolidate_warmup_stats_task())"
```

### Problème: Warmup n'avance pas

**Vérifier**:
```bash
# Stats des 7 derniers jours
SELECT * FROM warmup_daily_stats WHERE plan_id=1 ORDER BY date DESC LIMIT 7;

# Taux de bounce/spam
SELECT bounce_rate_7d, spam_rate_7d, paused FROM warmup_plans WHERE id=1;
```

### Problème: Pas d'alertes Telegram

**Vérifier**:
```bash
# Test bot Telegram
docker-compose exec api python -c "
from app.services.telegram_alerter import alerter
import asyncio
db = None
asyncio.run(alerter.send('Test warmup alert', db=db))
"
```

---

## Conclusion

✅ **Warmup Production Ready**

Les 3 corrections critiques ont été appliquées:
1. ✅ WarmupEngine professionnel intégré
2. ✅ Stats quotidiennes consolidées
3. ✅ Webhooks trackent les IPs en warmup

**Résultat**: Système de warmup enterprise-grade complet, automatisé, et scalable.

**Prochaine étape**: Déployer et démarrer avec 1 domaine!
