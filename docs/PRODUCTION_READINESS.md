# Production Readiness - Warmup & Évolution Progressive

## ✅ Warmup - État Actuel

### Système de Warmup Existant (COMPLET)

Vous avez **DÉJÀ** un système de warmup professionnel dans `app/services/warmup_engine.py`:

#### Caractéristiques du WarmupEngine

```python
✅ Progression sur 6 semaines
✅ Quotas progressifs configurables (.env)
✅ Vérification des taux de bounce (< 5%)
✅ Vérification des taux de spam (< 0.1%)
✅ Pause automatique si seuils dépassés
✅ Reprise automatique après période de pause
✅ Stats quotidiennes (sent, delivered, bounced, complaints, opens, clicks)
✅ Alertes Telegram en cas de problème
✅ Passage automatique WARMING → ACTIVE
```

#### Configuration Actuelle (.env)

```env
WARMUP_WEEK1_QUOTA=50         # Semaine 1: 50/jour
WARMUP_WEEK2_QUOTA=200        # Semaine 2: 200/jour
WARMUP_WEEK3_QUOTA=500        # Semaine 3: 500/jour
WARMUP_WEEK4_QUOTA=1500       # Semaine 4: 1500/jour
WARMUP_WEEK5_QUOTA=5000       # Semaine 5: 5000/jour
WARMUP_WEEK6_QUOTA=10000      # Semaine 6: 10000/jour
WARMUP_MAX_BOUNCE_RATE=5.0    # Max 5% bounces
WARMUP_MAX_SPAM_RATE=0.1      # Max 0.1% complaints
```

### ⚠️ PROBLÈME IDENTIFIÉ

**Le warmup engine N'EST PAS utilisé dans la tâche Celery!**

Dans `src/infrastructure/background/tasks.py`, la fonction `advance_warmup_task()` a une **logique simplifiée** avec un TODO:

```python
# TODO: Implement proper advancement logic from warmup_engine service
current_phase = warmup_plan.phase
current_quota = warmup_plan.current_daily_quota

# Simple advancement: double quota if < target
if current_quota < warmup_plan.target_daily_quota:
    new_quota = min(current_quota * 2, warmup_plan.target_daily_quota)
```

**Cette logique est INCORRECTE pour la production!**

---

## 🔧 Corrections Nécessaires pour Production

### 1. Intégrer WarmupEngine dans la tâche Celery (PRIORITÉ 1)

**Fichier à corriger**: `src/infrastructure/background/tasks.py`

```python
@celery_app.task(name="src.infrastructure.background.tasks.advance_warmup_task")
def advance_warmup_task() -> dict:
    """
    Advance IP warmup (periodic task - daily).
    Uses the professional WarmupEngine from app.services.warmup_engine
    """
    import asyncio
    from app.database import SessionLocal
    from app.services.warmup_engine import WarmupEngine

    db = SessionLocal()
    try:
        # Create engine
        engine = WarmupEngine(db)

        # Run daily tick (async)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(engine.daily_tick())

        return {"success": True, "message": "Warmup advanced successfully"}

    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}
    finally:
        db.close()
```

### 2. Enregistrer les Stats Quotidiennes (PRIORITÉ 1)

**Nouveau fichier**: `src/infrastructure/background/tasks.py` (ajouter)

```python
@celery_app.task(name="src.infrastructure.background.tasks.record_warmup_stats_task")
def record_warmup_stats_task(ip_id: int, stats: dict) -> dict:
    """
    Record daily warmup stats for an IP.

    Args:
        ip_id: IP ID
        stats: {
            "sent": 50,
            "delivered": 48,
            "bounced": 2,
            "complaints": 0,
            "opens": 25,
            "clicks": 10
        }
    """
    from app.database import SessionLocal
    from app.models import IP, WarmupPlan
    from app.services.warmup_engine import WarmupEngine

    db = SessionLocal()
    try:
        ip = db.query(IP).filter_by(id=ip_id).first()
        if not ip or not ip.warmup_plan:
            return {"success": False, "error": "IP or warmup plan not found"}

        engine = WarmupEngine(db)
        stat = engine.record_daily_stats(
            plan=ip.warmup_plan,
            sent=stats.get("sent", 0),
            delivered=stats.get("delivered", 0),
            bounced=stats.get("bounced", 0),
            complaints=stats.get("complaints", 0),
            opens=stats.get("opens", 0),
            clicks=stats.get("clicks", 0),
        )

        return {"success": True, "stat_id": stat.id}

    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}
    finally:
        db.close()
```

### 3. Configurer Celery Beat (PRIORITÉ 1)

**Fichier à créer/modifier**: `src/infrastructure/background/celery_app.py`

```python
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    'advance-warmup-daily': {
        'task': 'src.infrastructure.background.tasks.advance_warmup_task',
        'schedule': crontab(hour=1, minute=0),  # Tous les jours à 1h du matin
    },
}
```

### 4. Webhooks → Warmup Stats (PRIORITÉ 2)

**Fichier à modifier**: `src/presentation/api/v2/webhooks.py`

Quand vous recevez des événements MailWizz/PowerMTA, il faut **agréger les stats quotidiennes** et les enregistrer pour le warmup:

```python
# Dans mailwizz_webhook() et powermta_webhook()
# Après avoir créé l'événement, vérifier si l'IP est en warmup

from app.models import IP

# Retrouver l'IP qui a envoyé l'email (via metadata)
ip_address = metadata.get("sending_ip")  # À récupérer depuis PowerMTA
if ip_address:
    ip = db.query(IP).filter(IP.address == ip_address, IP.status == "warming").first()
    if ip and ip.warmup_plan:
        # Incrémenter les compteurs quotidiens dans Redis
        from src.infrastructure.cache import get_cache
        cache = get_cache()

        today = datetime.utcnow().date().isoformat()
        key = f"warmup:ip:{ip.id}:date:{today}"

        if event_type == EventType.DELIVERED:
            cache.increment(f"{key}:delivered")
        elif event_type == EventType.BOUNCED:
            cache.increment(f"{key}:bounced")
        elif event_type == EventType.COMPLAINED:
            cache.increment(f"{key}:complaints")
        elif event_type == EventType.OPENED:
            cache.increment(f"{key}:opens")
        elif event_type == EventType.CLICKED:
            cache.increment(f"{key}:clicks")
```

### 5. Tâche de Consolidation Quotidienne (PRIORITÉ 2)

**Nouveau endpoint**: Tâche Celery qui consolide les stats Redis → PostgreSQL chaque jour

```python
@celery_app.task(name="src.infrastructure.background.tasks.consolidate_warmup_stats_task")
def consolidate_warmup_stats_task() -> dict:
    """
    Consolidate Redis warmup counters to PostgreSQL (runs daily).

    Reads all warmup:ip:*:date:* keys from Redis and saves to WarmupDailyStat.
    """
    from app.database import SessionLocal
    from app.models import IP
    from app.services.warmup_engine import WarmupEngine
    from src.infrastructure.cache import get_cache
    from datetime import datetime, timedelta

    db = SessionLocal()
    cache = get_cache()

    try:
        # Get all warming IPs
        warming_ips = db.query(IP).filter(IP.status == "warming").all()

        yesterday = (datetime.utcnow() - timedelta(days=1)).date().isoformat()

        for ip in warming_ips:
            if not ip.warmup_plan:
                continue

            key_prefix = f"warmup:ip:{ip.id}:date:{yesterday}"

            sent = cache.get(f"{key_prefix}:sent") or 0
            delivered = cache.get(f"{key_prefix}:delivered") or 0
            bounced = cache.get(f"{key_prefix}:bounced") or 0
            complaints = cache.get(f"{key_prefix}:complaints") or 0
            opens = cache.get(f"{key_prefix}:opens") or 0
            clicks = cache.get(f"{key_prefix}:clicks") or 0

            if sent > 0:  # Only record if there was activity
                engine = WarmupEngine(db)
                engine.record_daily_stats(
                    plan=ip.warmup_plan,
                    sent=sent,
                    delivered=delivered,
                    bounced=bounced,
                    complaints=complaints,
                    opens=opens,
                    clicks=clicks,
                )

                # Delete Redis keys after consolidation
                cache.delete_pattern(f"{key_prefix}:*")

        return {"success": True, "ips_processed": len(warming_ips)}

    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}
    finally:
        db.close()


# Ajouter au beat_schedule:
celery_app.conf.beat_schedule['consolidate-warmup-stats'] = {
    'task': 'src.infrastructure.background.tasks.consolidate_warmup_stats_task',
    'schedule': crontab(hour=0, minute=30),  # Tous les jours à 0h30
}
```

---

## 📈 Évolution Progressive: 5 Domaines → 50+ Domaines

### Stratégie Recommandée

#### Phase 1: Démarrage avec 5 Domaines (Semaines 1-6)

```python
# Seed initial
tenant = SOS-Expat (id=1)
domains = [
    "mail1.sos-mail.com",
    "mail2.sos-mail.com",
    "mail3.sos-mail.com",
    "mail4.sos-mail.com",
    "mail5.sos-mail.com",
]
ips = [
    "45.123.10.1",  # mail1
    "45.123.10.2",  # mail2
    "45.123.10.3",  # mail3
    "45.123.10.4",  # mail4
    "45.123.10.5",  # mail5
]

# Warmup: 1 IP/domaine par semaine (rotation)
Week 1: Warm IP 45.123.10.1 (mail1.sos-mail.com)
Week 2: Warm IP 45.123.10.2 (mail2.sos-mail.com) + continue IP1
Week 3: Warm IP 45.123.10.3 (mail3.sos-mail.com) + continue IP1-2
Week 4: Warm IP 45.123.10.4 (mail4.sos-mail.com) + continue IP1-3
Week 5: Warm IP 45.123.10.5 (mail5.sos-mail.com) + continue IP1-4
Week 6: All 5 IPs in warmup, IP1 becomes ACTIVE
```

#### Phase 2: Ajout Progressif (Semaines 7-42)

**Règle**: Ajouter **1 nouveau domaine/IP par semaine** max

```python
# Script: scripts/add_domain.py

def add_new_domain_with_ip(tenant_id: int, domain_name: str, ip_address: str):
    """
    Add a new domain + IP and start warmup.

    Usage:
        python scripts/add_domain.py --tenant 1 --domain mail6.sos-mail.com --ip 45.123.10.6
    """
    from app.database import SessionLocal
    from app.models import Domain, IP, WarmupPlan
    from app.enums import DomainStatus, IPStatus, WarmupPhase
    from app.services.warmup_engine import WarmupEngine

    db = SessionLocal()
    try:
        # 1. Create domain
        domain = Domain(
            tenant_id=tenant_id,
            domain=domain_name,
            status=DomainStatus.WARMING.value,
        )
        db.add(domain)
        db.flush()

        # 2. Create IP
        ip = IP(
            tenant_id=tenant_id,
            address=ip_address,
            domain_id=domain.id,
            status=IPStatus.WARMING.value,
            weight=0,  # Will be 100 after warmup
        )
        db.add(ip)
        db.flush()

        # 3. Create warmup plan
        engine = WarmupEngine(db)
        plan = engine.create_plan(ip)

        db.commit()

        print(f"✅ Domain {domain_name} + IP {ip_address} created and warmup started")
        print(f"   - Warmup Phase: {plan.phase}")
        print(f"   - Daily Quota: {plan.current_daily_quota}")
        print(f"   - Target: {plan.target_daily_quota}/day in 6 weeks")

    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
    finally:
        db.close()
```

**Utilisation**:

```bash
# Semaine 7: Ajouter 6ème domaine
docker-compose exec api python scripts/add_domain.py \
  --tenant 1 \
  --domain mail6.sos-mail.com \
  --ip 45.123.10.6

# Semaine 8: Ajouter 7ème domaine
docker-compose exec api python scripts/add_domain.py \
  --tenant 1 \
  --domain mail7.sos-mail.com \
  --ip 45.123.10.7

# etc...
```

#### Phase 3: Monitoring de la Montée en Charge

**API Endpoint pour surveiller la progression**:

```bash
# Voir tous les domaines/IPs en warmup
curl http://localhost:8000/api/v1/warmup

# Response:
{
  "warming_ips": [
    {
      "ip": "45.123.10.1",
      "domain": "mail1.sos-mail.com",
      "phase": "completed",
      "status": "active",
      "daily_quota": 10000,
      "warmup_duration_days": 42
    },
    {
      "ip": "45.123.10.6",
      "domain": "mail6.sos-mail.com",
      "phase": "week_2",
      "status": "warming",
      "daily_quota": 200,
      "warmup_duration_days": 14
    }
  ],
  "active_ips": 5,
  "warming_ips": 1,
  "total_daily_capacity": 50200  # 5×10000 + 1×200
}
```

---

## 🚨 Ce qui Manque pour Production Ready

### CRITIQUES (Bloquer le déploiement)

1. **❌ Warmup Engine non connecté à Celery**
   - Statut: TODO dans le code
   - Impact: Warmup ne fonctionne pas correctement
   - Solution: Voir corrections ci-dessus
   - Temps: 2-3 heures

2. **❌ Stats quotidiennes non enregistrées**
   - Statut: Pas de consolidation Redis → PostgreSQL
   - Impact: Pas de tracking du warmup
   - Solution: Tâche `consolidate_warmup_stats_task`
   - Temps: 1-2 heures

3. **❌ Webhooks ne trackent pas les IPs en warmup**
   - Statut: Événements créés mais pas liés au warmup
   - Impact: Pas de données pour avancer les phases
   - Solution: Modifier webhooks pour incrémenter Redis
   - Temps: 2-3 heures

### IMPORTANTES (Déployer mais surveiller)

4. **⚠️ Alertes Telegram non testées**
   - Statut: Code existe mais pas de `TELEGRAM_BOT_TOKEN` en .env
   - Impact: Pas d'alertes en cas de problème warmup
   - Solution: Configurer bot Telegram
   - Temps: 30 minutes

5. **⚠️ Pas de dashboard warmup visuel**
   - Statut: API existe mais pas de frontend
   - Impact: Monitoring via API seulement
   - Solution: Créer page React simple
   - Temps: 4-6 heures (optionnel)

6. **⚠️ PowerMTA config non générée automatiquement**
   - Statut: Service existe mais pas appelé
   - Impact: Configuration manuelle nécessaire
   - Solution: Endpoint pour générer config
   - Temps: 1 heure

### NICE-TO-HAVE (Post-lancement)

7. **💡 Tests end-to-end warmup**
   - Statut: Pas de tests automatisés
   - Impact: Risque de régressions
   - Solution: Suite de tests pytest
   - Temps: 4-6 heures

8. **💡 Simulation de warmup (mode test)**
   - Statut: N'existe pas
   - Impact: Impossible de tester sans vrais envois
   - Solution: Mode dry-run
   - Temps: 2-3 heures

9. **💡 Rollback automatique en cas d'échec**
   - Statut: Pause existe mais pas de rollback
   - Impact: Manual intervention nécessaire
   - Solution: Auto-rollback à phase précédente
   - Temps: 3-4 heures

---

## ✅ Plan d'Action Production

### Sprint 1 (Avant Production) - 1 jour

```
✅ Intégrer WarmupEngine dans advance_warmup_task (3h)
✅ Créer consolidate_warmup_stats_task (2h)
✅ Modifier webhooks pour tracker warmup (3h)
✅ Configurer Telegram bot (30min)
✅ Créer script add_domain.py (1h)
✅ Tests manuels du warmup (2h)

TOTAL: ~11h30 (1 journée de travail)
```

### Sprint 2 (Post-Production) - 2 jours

```
⚠️ Endpoint pour générer PowerMTA config (1h)
⚠️ Dashboard warmup simple (6h)
⚠️ Tests end-to-end (6h)
⚠️ Documentation utilisateur (2h)

TOTAL: ~15h (2 jours de travail)
```

### Sprint 3 (Optimisation) - 1 jour

```
💡 Mode simulation/dry-run (3h)
💡 Rollback automatique (4h)
💡 Monitoring Prometheus/Grafana (4h)

TOTAL: ~11h (1 jour de travail)
```

---

## 📝 Checklist Production

### Avant Déploiement

- [ ] Corriger `advance_warmup_task` avec WarmupEngine
- [ ] Créer `consolidate_warmup_stats_task`
- [ ] Modifier webhooks pour tracker warmup
- [ ] Configurer Celery Beat schedule
- [ ] Configurer `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID`
- [ ] Créer `scripts/add_domain.py`
- [ ] Tester warmup sur 1 IP pendant 7 jours
- [ ] Configurer quotas warmup dans .env
- [ ] Configurer seuils bounce/spam dans .env

### Premier Jour de Production

- [ ] Démarrer avec 1 seul domaine/IP
- [ ] Vérifier quotas respectés (50 emails/jour)
- [ ] Vérifier stats dans PostgreSQL
- [ ] Vérifier alertes Telegram
- [ ] Surveiller taux de bounce (< 5%)
- [ ] Surveiller taux de spam (< 0.1%)

### Première Semaine

- [ ] Ajouter 1 nouveau domaine/IP par jour (5 total)
- [ ] Vérifier avancement automatique des phases
- [ ] Monitorer capacité totale quotidienne
- [ ] Ajuster quotas si nécessaire

### Après 6 Semaines

- [ ] Tous les 5 premiers IPs devraient être ACTIVE
- [ ] Capacité: 5 × 10,000 = 50,000 emails/jour
- [ ] Commencer à ajouter 1 nouveau domaine/semaine
- [ ] Objectif: 50 domaines en 1 an

---

## 🎯 Résumé

### ✅ Ce qui est DÉJÀ bien fait

- Architecture complète (Clean Architecture)
- WarmupEngine professionnel avec toutes les features
- Gestion multi-tenant parfaite
- Système de pause/reprise automatique
- Alertes configurées
- Stats tracking prévu
- Évolution progressive possible

### ❌ Ce qui DOIT être corrigé (BLOQUANT)

1. Connecter WarmupEngine à la tâche Celery
2. Créer la consolidation des stats Redis → PostgreSQL
3. Modifier les webhooks pour tracker les IPs en warmup

**Temps total: ~8 heures de travail**

### Évolution 5 → 50+ domaines

**Stratégie validée**:
- Semaines 1-5: Warmup 5 premiers domaines (1/semaine)
- Semaines 6-42: 5 IPs actifs + warmup progressif
- Semaines 7+: Ajouter 1 nouveau domaine/semaine max
- Année 1: 50 domaines opérationnels
- Monitoring continu avec API + alertes Telegram

**Capacité finale**: 50 domaines × 10,000 emails/jour = **500,000 emails/jour**

---

Voulez-vous que je crée les scripts de correction maintenant pour rendre le warmup production-ready?
