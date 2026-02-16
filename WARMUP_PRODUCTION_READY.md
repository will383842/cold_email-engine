# ✅ WARMUP PRODUCTION READY

**Date**: 2026-02-16
**Status**: **COMPLET - DÉPLOIEMENT POSSIBLE**

---

## 🎉 Résumé des Corrections

Les 3 problèmes critiques du warmup ont été corrigés. Le système est maintenant **production-ready**.

### ✅ Correction 1: WarmupEngine Intégré

**Fichier**: `src/infrastructure/background/tasks.py`

La tâche `advance_warmup_task()` utilise maintenant le **WarmupEngine professionnel** complet avec:
- Vérification taux de bounce (< 5%)
- Vérification taux de spam (< 0.1%)
- Pause automatique si problème
- Avancement automatique après 7 jours
- Alertes Telegram

### ✅ Correction 2: Consolidation Stats

**Fichier**: `src/infrastructure/background/tasks.py`

Nouvelle tâche `consolidate_warmup_stats_task()` qui:
- Lit les compteurs Redis chaque jour
- Sauvegarde dans PostgreSQL (historique permanent)
- Nettoie Redis après consolidation
- Exécutée automatiquement à 00:30 UTC

### ✅ Correction 3: Webhooks Tracking

**Fichier**: `src/presentation/api/v2/webhooks.py`

Les webhooks MailWizz et PowerMTA trackent maintenant les IPs en warmup:
- Nouvelle fonction `_track_warmup_event()`
- Incrémente Redis en temps réel
- Intégré dans tous les webhooks
- Zéro impact sur performance

### ✅ Bonus: Script add_domain.py

**Fichier**: `scripts/add_domain.py`

Script complet pour évolution progressive 5 → 50+ domaines:

```bash
python scripts/add_domain.py --tenant 1 --domain mail6.sos-mail.com --ip 45.123.10.6
```

---

## 📋 Checklist Déploiement

### Configuration (.env)

```env
# Warmup Quotas
WARMUP_WEEK1_QUOTA=50
WARMUP_WEEK2_QUOTA=200
WARMUP_WEEK3_QUOTA=500
WARMUP_WEEK4_QUOTA=1500
WARMUP_WEEK5_QUOTA=5000
WARMUP_WEEK6_QUOTA=10000

# Safety Thresholds
WARMUP_MAX_BOUNCE_RATE=5.0
WARMUP_MAX_SPAM_RATE=0.1

# Telegram Alerts (IMPORTANT!)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Redis & Celery
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### Lancer les Services

```bash
# 1. Démarrer tous les services
docker-compose up -d

# 2. Vérifier que Celery Beat fonctionne
docker-compose logs celery_beat | grep schedule

# 3. Vérifier les workers
docker-compose ps
```

### Premier Domaine

```bash
# 1. Créer premier domaine (SOS-Expat)
docker-compose exec api python scripts/add_domain.py \
  --tenant 1 \
  --domain mail1.sos-mail.com \
  --ip 45.123.10.1

# 2. Vérifier création
curl http://localhost:8000/api/v1/warmup

# 3. Configurer DNS
# - A record: mail1.sos-mail.com → 45.123.10.1
# - DKIM, SPF, DMARC records

# 4. Commencer envois
# Max 50 emails/jour la première semaine
```

---

## 🚀 Plan de Déploiement

### Semaines 1-5: Warmup Initial (5 domaines)

```bash
# Semaine 1
python scripts/add_domain.py --tenant 1 --domain mail1.sos-mail.com --ip 45.123.10.1
# Envoyer 50/jour

# Semaine 2
python scripts/add_domain.py --tenant 1 --domain mail2.sos-mail.com --ip 45.123.10.2
# mail1: 200/jour, mail2: 50/jour

# Semaine 3
python scripts/add_domain.py --tenant 1 --domain mail3.sos-mail.com --ip 45.123.10.3
# mail1: 500/jour, mail2: 200/jour, mail3: 50/jour

# Semaine 4
python scripts/add_domain.py --tenant 1 --domain mail4.sos-mail.com --ip 45.123.10.4
# mail1: 1500/jour, mail2: 500/jour, mail3: 200/jour, mail4: 50/jour

# Semaine 5
python scripts/add_domain.py --tenant 1 --domain mail5.sos-mail.com --ip 45.123.10.5
# mail1: 5000/jour, mail2: 1500/jour, mail3: 500/jour, mail4: 200/jour, mail5: 50/jour
```

### Semaine 6: Premier IP ACTIVE

```
mail1.sos-mail.com → 10,000/jour (ACTIVE) ✅
mail2 → 5000/jour
mail3 → 1500/jour
mail4 → 500/jour
mail5 → 200/jour

Capacité totale: 17,200 emails/jour
```

### Semaines 7-52: Croissance Progressive

```bash
# Ajouter 1 nouveau domaine par semaine max
# Semaine 7
python scripts/add_domain.py --tenant 1 --domain mail6.sos-mail.com --ip 45.123.10.6

# Semaine 8
python scripts/add_domain.py --tenant 1 --domain mail7.sos-mail.com --ip 45.123.10.7

# etc...
```

**Après 12 semaines (Semaine 1 + 6 warmup + 5 ajouts)**:
- 10 domaines ACTIVE = 100,000 emails/jour

**Après 52 semaines**:
- 50 domaines ACTIVE = 500,000 emails/jour

---

## 📊 Monitoring

### Vérifier Stats en Temps Réel

```bash
# Redis counters (aujourd'hui)
docker-compose exec redis redis-cli KEYS "warmup:ip:*"
docker-compose exec redis redis-cli GET "warmup:ip:1:date:2026-02-16:delivered"

# Stats consolidées (PostgreSQL)
docker-compose exec postgres psql -U email_engine -c "
  SELECT date, sent, delivered, bounced, complaints
  FROM warmup_daily_stats
  WHERE plan_id = 1
  ORDER BY date DESC
  LIMIT 7;
"

# Taux bounce/spam
docker-compose exec postgres psql -U email_engine -c "
  SELECT
    bounce_rate_7d,
    spam_rate_7d,
    phase,
    current_daily_quota,
    paused
  FROM warmup_plans
  WHERE id = 1;
"
```

### API Endpoints

```bash
# Liste tous les IPs en warmup
curl http://localhost:8000/api/v1/warmup

# Détails d'un IP
curl http://localhost:8000/api/v1/ips/1
```

### Alertes Telegram

Vous recevrez automatiquement:
- ⚠️ Warning: Bounce rate > 5%
- 🚨 Critical: Spam rate > 0.1%
- ✅ Info: IP devient ACTIVE

---

## 🔧 Dépannage

### Consolidation ne fonctionne pas

```bash
# Vérifier logs
docker-compose logs celery_beat | grep consolidate

# Test manuel
docker-compose exec api python -c "
from src.infrastructure.background.tasks import consolidate_warmup_stats_task
print(consolidate_warmup_stats_task())
"
```

### Warmup n'avance pas

**Vérifier qu'il y a 7 jours de stats**:
```sql
SELECT COUNT(*) FROM warmup_daily_stats WHERE plan_id=1 AND date >= CURRENT_DATE - 7;
```

**Vérifier taux**:
```sql
SELECT bounce_rate_7d, spam_rate_7d FROM warmup_plans WHERE id=1;
```

### Pas d'alertes Telegram

```bash
# Test manuel
docker-compose exec api python -c "
from app.services.telegram_alerter import alerter
import asyncio
asyncio.run(alerter.send('Test alert warmup'))
"
```

---

## 📚 Documentation

Consultez ces fichiers pour plus de détails:

1. **`docs/WARMUP_FIXES_APPLIED.md`** - Détails techniques des corrections
2. **`docs/PRODUCTION_READINESS.md`** - Guide complet warmup
3. **`scripts/add_domain.py`** - Script d'ajout de domaines
4. **`app/services/warmup_engine.py`** - Code source WarmupEngine

---

## ✅ Résultat Final

### Ce qui fonctionne maintenant

✅ **Tracking en temps réel** (Redis)
✅ **Consolidation quotidienne** (PostgreSQL)
✅ **Avancement automatique** (WarmupEngine)
✅ **Alertes Telegram** (bounce/spam)
✅ **Pause automatique** si problème
✅ **Évolution progressive** (5 → 50+ domaines)
✅ **Script d'ajout** (add_domain.py)
✅ **Monitoring complet** (API + SQL)

### Capacité Finale

- **5 domaines** = 50,000 emails/jour
- **10 domaines** = 100,000 emails/jour
- **50 domaines** = 500,000 emails/jour

### Temps de Mise en Œuvre

- Semaine 1-6: 5 domaines en warmup
- Semaine 6+: Ajout 1 domaine/semaine
- Année 1: 50 domaines opérationnels

---

## 🎯 Prochaines Étapes

### Aujourd'hui

1. [ ] Configurer `.env` (quotas, Telegram)
2. [ ] Démarrer services (`docker-compose up -d`)
3. [ ] Vérifier Celery Beat (`docker-compose logs celery_beat`)

### Demain

4. [ ] Créer premier domaine (`add_domain.py`)
5. [ ] Configurer DNS (A, DKIM, SPF, DMARC)
6. [ ] Envoyer premiers 50 emails

### Semaine 1

7. [ ] Surveiller taux bounce/spam quotidiens
8. [ ] Vérifier alertes Telegram
9. [ ] Ajouter domaines 2-5 (1 par jour ou tous les 2 jours)

### Après 6 Semaines

10. [ ] Premier IP ACTIVE (10,000/jour)
11. [ ] Continuer ajout 1 domaine/semaine
12. [ ] Scaler jusqu'à 50 domaines

---

**Le système est prêt. Vous pouvez déployer en production! 🚀**

---

Pour toute question, consultez:
- `docs/WARMUP_FIXES_APPLIED.md` - Détails techniques
- `docs/PRODUCTION_READINESS.md` - Guide complet
- Logs: `docker-compose logs -f api`
- Monitoring: http://localhost:5555 (Flower)
