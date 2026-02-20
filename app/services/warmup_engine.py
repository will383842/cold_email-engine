"""
Warmup Engine — Hyper-protecteur (10 semaines, progression lente).

Philosophie :
  Mieux vaut 70 jours pour atteindre 10k/jour qu'une blacklist
  en 2 semaines qui coûte 6 mois de récupération de réputation.

Progression quotidienne :
  - Intra-semaine : quota augmente chaque jour (pas fixe)
  - Envoi étalé sur 16h actives (7h-23h) pour éviter les pics
  - Seuils ultra-stricts : bounce > 2%, spam > 0.03% → pause immédiate
  - Arrêt d'urgence : bounce > 5% ou spam > 0.1% sur 24h → quarantine

Architecture multi-IP :
  Chaque IP a son propre plan warmup indépendant.
  La synchronisation avec MailWizz (quotas) se fait automatiquement.
"""

from datetime import datetime, timedelta

import structlog
from sqlalchemy.orm import Session

from app.config import settings
from app.enums import AlertCategory, AlertSeverity, IPStatus
from app.models import IP, WarmupDailyStat, WarmupPlan
from app.services.mailwizz_db import mailwizz_db
from app.services.telegram_alerter import alerter

logger = structlog.get_logger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# PLANNING QUOTAS JOURNALIERS — 70 jours (10 semaines)
#
# Chaque valeur = quota maximum pour ce jour précis.
# La progression est délibérément lente et régulière pour construire
# une réputation solide auprès des ISPs.
# ─────────────────────────────────────────────────────────────────────────────
DAILY_QUOTAS: list[int] = [
    # Semaine 1 : démarrage très doux (5→20)
    5, 7, 10, 12, 15, 18, 20,
    # Semaine 2 : montée douce (25→50)
    25, 28, 32, 36, 40, 45, 50,
    # Semaine 3 : accélération modérée (55→110)
    55, 65, 75, 85, 95, 100, 110,
    # Semaine 4 : montée régulière (125→250)
    125, 140, 160, 180, 200, 225, 250,
    # Semaine 5 : cap des 500 (280→550)
    280, 320, 360, 400, 450, 500, 550,
    # Semaine 6 : cap des 1000 (600→1200)
    600, 700, 800, 900, 1000, 1100, 1200,
    # Semaine 7 : cap des 2500 (1400→2600)
    1400, 1600, 1800, 2000, 2200, 2400, 2600,
    # Semaine 8 : cap des 5000 (2800→5500)
    2800, 3200, 3600, 4000, 4500, 5000, 5500,
    # Semaine 9 : cap des 10000 (6000→10000)
    6000, 6500, 7000, 7500, 8000, 9000, 10000,
    # Semaine 10 : IP mature — peut monter librement
    11000, 12500, 14000, 15500, 17000, 18500, 20000,
]

WARMUP_TOTAL_DAYS = len(DAILY_QUOTAS)  # 70 jours


def get_quota_for_day(day_number: int) -> int:
    """
    Retourne le quota journalier pour le jour N du warmup (1-indexed).

    Après les 70 jours, l'IP est considérée mature et le quota final s'applique.
    """
    if day_number <= 0:
        return DAILY_QUOTAS[0]
    if day_number > WARMUP_TOTAL_DAYS:
        return DAILY_QUOTAS[-1]
    return DAILY_QUOTAS[day_number - 1]


def daily_to_hourly_quota(daily: int) -> int:
    """
    Convertit un quota journalier en quota horaire pour MailWizz.

    Principe : envoi étalé sur 16h actives (7h→23h) avec 20% de marge.
    Cela évite les pics de volume qui alertent les filtres ISP.

    Ex: 50/jour → max 50/16 = 3/heure
        1000/jour → max 1000/16 = 62/heure
    """
    return max(1, int(daily / 16 * 0.80))


# ─────────────────────────────────────────────────────────────────────────────
# WARMUP ENGINE
# ─────────────────────────────────────────────────────────────────────────────

class WarmupEngine:
    """
    Moteur de warmup progressif pour les IPs d'envoi.

    Gère la progression quotidienne automatique, les vérifications
    de sécurité et la synchronisation avec MailWizz.
    """

    def __init__(self, db: Session):
        self.db = db

    # ─────────────────────────────────────────────────────
    # Création du plan
    # ─────────────────────────────────────────────────────

    def create_plan(self, ip: IP) -> WarmupPlan:
        """
        Crée un plan warmup pour une nouvelle IP.
        Démarre à jour 1 avec le quota minimal (5 emails).
        """
        initial_quota = DAILY_QUOTAS[0]
        plan = WarmupPlan(
            tenant_id=ip.tenant_id,
            ip_id=ip.id,
            phase="day_1",
            started_at=datetime.utcnow(),
            current_daily_quota=initial_quota,
            target_daily_quota=DAILY_QUOTAS[-1],
        )
        self.db.add(plan)
        self.db.commit()
        self.db.refresh(plan)
        logger.info(
            "warmup_plan_created",
            ip=ip.address,
            initial_quota=initial_quota,
            total_days=WARMUP_TOTAL_DAYS,
        )
        return plan

    # ─────────────────────────────────────────────────────
    # Enregistrement des stats
    # ─────────────────────────────────────────────────────

    def record_daily_stats(
        self,
        plan: WarmupPlan,
        sent: int,
        delivered: int,
        bounced: int,
        complaints: int,
        opens: int = 0,
        clicks: int = 0,
    ) -> WarmupDailyStat:
        """
        Enregistre les statistiques d'envoi du jour.
        À appeler une fois par jour après le bilan nocturne.
        """
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        # Vérifier si les stats du jour existent déjà (upsert)
        existing = (
            self.db.query(WarmupDailyStat)
            .filter(WarmupDailyStat.plan_id == plan.id, WarmupDailyStat.date == today)
            .first()
        )
        if existing:
            existing.sent = sent
            existing.delivered = delivered
            existing.bounced = bounced
            existing.complaints = complaints
            existing.opens = opens
            existing.clicks = clicks
            self.db.commit()
            return existing

        stat = WarmupDailyStat(
            plan_id=plan.id,
            date=today,
            sent=sent,
            delivered=delivered,
            bounced=bounced,
            complaints=complaints,
            opens=opens,
            clicks=clicks,
        )
        self.db.add(stat)
        self.db.commit()
        return stat

    # ─────────────────────────────────────────────────────
    # Calcul du numéro de jour actuel
    # ─────────────────────────────────────────────────────

    def _get_day_number(self, plan: WarmupPlan) -> int:
        """
        Calcule le numéro de jour actuel dans le warmup (1-indexed).

        IMPORTANT : Ne compte pas les jours de pause — le warmup reprend
        au bon endroit après une pause (pas de quota perdu).

        Stocke `pause_accumulated_days` dans les metadata du plan via
        le champ `bounce_rate_7d` est une autre approche, mais on utilise
        directement `paused_total_days` stocké dans le model si disponible.
        Si le champ n'existe pas, on approche via `pause_until - started_at`.
        """
        if not plan.started_at:
            return 1

        now = datetime.utcnow()
        calendar_days = (now - plan.started_at).days

        # Déduire les jours de pause accumulés
        # On cherche dans les stats journalières le nombre de jours où
        # paused=True a été en vigueur. Approche simple : compter les
        # jours sans stats (== jours de pause).
        stats_days = (
            self.db.query(WarmupDailyStat)
            .filter(WarmupDailyStat.plan_id == plan.id)
            .count()
        )

        # stats_days = nombre de jours où l'IP a effectivement envoyé
        # Si pause au jour 10, les jours 11+12+13 n'ont pas de stats
        # Donc : day_number = stats_days + 1 (prochain jour à envoyer)
        # Mais si jamais de stats : utiliser le calcul calendaire brut
        if stats_days > 0:
            effective_day = stats_days + 1
        else:
            effective_day = max(1, calendar_days + 1)

        return min(effective_day, WARMUP_TOTAL_DAYS + 1)

    # ─────────────────────────────────────────────────────
    # Vérifications de sécurité (seuils hyper-stricts)
    # ─────────────────────────────────────────────────────

    def _compute_rates(self, plan: WarmupPlan, days: int = 7) -> tuple[float, float]:
        """Calcule les taux de bounce et spam sur les N derniers jours."""
        since = datetime.utcnow() - timedelta(days=days)
        stats = (
            self.db.query(WarmupDailyStat)
            .filter(WarmupDailyStat.plan_id == plan.id, WarmupDailyStat.date >= since)
            .all()
        )
        total_sent = sum(s.sent for s in stats)
        total_bounced = sum(s.bounced for s in stats)
        total_complaints = sum(s.complaints for s in stats)

        bounce_rate = (total_bounced / total_sent * 100) if total_sent > 0 else 0.0
        spam_rate = (total_complaints / total_sent * 100) if total_sent > 0 else 0.0
        return round(bounce_rate, 3), round(spam_rate, 3)

    def _compute_24h_rates(self, plan: WarmupPlan) -> tuple[float, float]:
        """Calcule les taux sur les dernières 24h (détection d'urgence)."""
        return self._compute_rates(plan, days=1)

    async def check_safety(self, plan: WarmupPlan) -> bool:
        """
        Vérifie les seuils de sécurité.

        Niveaux de réponse :
          1. bounce > EMERGENCY ou spam > EMERGENCY → quarantine immédiate 30j
          2. bounce > MAX ou spam > MAX → pause 72-96h
          3. OK → continuer

        Retourne True si l'envoi peut continuer, False si mis en pause/quarantine.
        """
        ip = self.db.query(IP).filter(IP.id == plan.ip_id).first()
        ip_addr = ip.address if ip else "unknown"

        # Mise à jour des métriques 7j
        bounce_7d, spam_7d = self._compute_rates(plan, days=7)
        plan.bounce_rate_7d = bounce_7d
        plan.spam_rate_7d = spam_7d

        # Vérification d'urgence sur 24h (arrêt total)
        bounce_24h, spam_24h = self._compute_24h_rates(plan)

        if bounce_24h > settings.WARMUP_EMERGENCY_BOUNCE_RATE:
            await self._emergency_stop(plan, ip, f"BOUNCE CRITIQUE : {bounce_24h:.1f}%/24h")
            return False

        if spam_24h > settings.WARMUP_EMERGENCY_SPAM_RATE:
            await self._emergency_stop(plan, ip, f"SPAM CRITIQUE : {spam_24h:.2f}%/24h")
            return False

        # Vérification des seuils normaux sur 7j (pause temporaire)
        if bounce_7d > settings.WARMUP_MAX_BOUNCE_RATE:
            pause_hours = settings.WARMUP_PAUSE_BOUNCE_HOURS
            plan.paused = True
            plan.pause_until = datetime.utcnow() + timedelta(hours=pause_hours)
            self.db.commit()
            await alerter.send(
                f"⚠️ Warmup pausé *{ip_addr}*\n"
                f"Bounce 7j : *{bounce_7d:.1f}%* > seuil {settings.WARMUP_MAX_BOUNCE_RATE}%\n"
                f"Reprise dans {pause_hours}h",
                severity=AlertSeverity.WARNING,
                category=AlertCategory.WARMUP,
                db=self.db,
            )
            # Désactiver temporairement le delivery server MailWizz
            if ip and ip.mailwizz_server_id:
                await mailwizz_db.pause_delivery_server(ip.mailwizz_server_id)
            return False

        if spam_7d > settings.WARMUP_MAX_SPAM_RATE:
            pause_hours = settings.WARMUP_PAUSE_SPAM_HOURS
            plan.paused = True
            plan.pause_until = datetime.utcnow() + timedelta(hours=pause_hours)
            self.db.commit()
            await alerter.send(
                f"🚨 Warmup pausé *{ip_addr}* — SPAM\n"
                f"Spam 7j : *{spam_7d:.3f}%* > seuil {settings.WARMUP_MAX_SPAM_RATE}%\n"
                f"Reprise dans {pause_hours}h — Analyser IMMÉDIATEMENT les listes",
                severity=AlertSeverity.CRITICAL,
                category=AlertCategory.WARMUP,
                db=self.db,
            )
            if ip and ip.mailwizz_server_id:
                await mailwizz_db.pause_delivery_server(ip.mailwizz_server_id)
            return False

        self.db.commit()
        return True

    async def _emergency_stop(self, plan: WarmupPlan, ip: IP | None, reason: str) -> None:
        """
        Arrêt d'urgence : quarantine 30j + désactivation immédiate.
        Utilisé quand les seuils critiques (24h) sont dépassés.
        """
        plan.paused = True
        plan.pause_until = datetime.utcnow() + timedelta(days=30)
        plan.phase = "emergency_stop"

        if ip:
            ip.status = IPStatus.QUARANTINED.value
            ip.quarantine_until = datetime.utcnow() + timedelta(days=30)
            ip.status_changed_at = datetime.utcnow()

            # Désactiver immédiatement le delivery server MailWizz
            if ip.mailwizz_server_id:
                await mailwizz_db.pause_delivery_server(ip.mailwizz_server_id)

        self.db.commit()

        await alerter.send(
            f"🆘 ARRÊT D'URGENCE IP *{ip.address if ip else 'unknown'}*\n"
            f"Raison : {reason}\n"
            f"Action : IP mise en QUARANTINE 30 jours\n"
            f"MailWizz delivery server désactivé\n"
            f"⚡ Vérifier IMMÉDIATEMENT les listes + PowerMTA logs",
            severity=AlertSeverity.CRITICAL,
            category=AlertCategory.WARMUP,
            db=self.db,
        )
        logger.error(
            "warmup_emergency_stop",
            ip=ip.address if ip else "unknown",
            reason=reason,
        )

    # ─────────────────────────────────────────────────────
    # Avancement quotidien
    # ─────────────────────────────────────────────────────

    async def advance_day(self, plan: WarmupPlan) -> bool:
        """
        Avance le warmup au jour suivant si toutes les conditions sont remplies.

        Conditions :
          1. Le plan n'est pas en pause
          2. Les seuils de sécurité sont OK
          3. Au moins 1 jour de stats disponible

        Retourne True si l'avancement a eu lieu.
        """
        ip = self.db.query(IP).filter(IP.id == plan.ip_id).first()

        if plan.phase == "completed":
            return False

        if plan.phase == "emergency_stop":
            return False

        # Vérifier sécurité
        safe = await self.check_safety(plan)
        if not safe:
            return False

        # Calculer le jour actuel
        day_number = self._get_day_number(plan)

        if day_number > WARMUP_TOTAL_DAYS:
            # Warmup terminé !
            await self._complete_warmup(plan, ip)
            return True

        # Mettre à jour le quota journalier
        new_quota = get_quota_for_day(day_number)
        plan.current_daily_quota = new_quota
        plan.phase = f"day_{day_number}"
        self.db.commit()

        # Synchroniser le quota vers MailWizz
        if ip and ip.mailwizz_server_id:
            await mailwizz_db.sync_warmup_quota(ip.mailwizz_server_id, new_quota)

        logger.info(
            "warmup_day_advanced",
            ip=ip.address if ip else "unknown",
            day=day_number,
            quota=new_quota,
            hourly=daily_to_hourly_quota(new_quota),
        )
        return True

    async def _complete_warmup(self, plan: WarmupPlan, ip: IP | None) -> None:
        """Marque le warmup comme terminé et active l'IP."""
        plan.phase = "completed"
        plan.current_daily_quota = DAILY_QUOTAS[-1]

        if ip:
            ip.status = IPStatus.ACTIVE.value
            ip.status_changed_at = datetime.utcnow()

        self.db.commit()

        # Mettre le quota MailWizz au maximum
        if ip and ip.mailwizz_server_id:
            await mailwizz_db.sync_warmup_quota(ip.mailwizz_server_id, DAILY_QUOTAS[-1])
            await mailwizz_db.resume_delivery_server(ip.mailwizz_server_id)

        await alerter.send(
            f"✅ Warmup terminé pour *{ip.address if ip else 'unknown'}*\n"
            f"Durée : 70 jours\n"
            f"IP maintenant ACTIVE — quota : {DAILY_QUOTAS[-1]:,} emails/jour",
            severity=AlertSeverity.INFO,
            category=AlertCategory.WARMUP,
            db=self.db,
        )
        logger.info("warmup_completed", ip=ip.address if ip else "unknown")

    async def resume_paused_plan(self, plan: WarmupPlan) -> bool:
        """
        Reprend un plan mis en pause si le délai est écoulé.
        Réactive le delivery server MailWizz correspondant.
        """
        if not plan.paused or not plan.pause_until:
            return False
        if plan.pause_until > datetime.utcnow():
            return False  # Délai pas encore écoulé

        plan.paused = False
        plan.pause_until = None
        self.db.commit()

        ip = self.db.query(IP).filter(IP.id == plan.ip_id).first()
        if ip and ip.mailwizz_server_id:
            await mailwizz_db.resume_delivery_server(ip.mailwizz_server_id)

        await alerter.send(
            f"▶️ Warmup repris pour *{ip.address if ip else 'unknown'}*",
            severity=AlertSeverity.INFO,
            category=AlertCategory.WARMUP,
            db=self.db,
        )
        return True

    # ─────────────────────────────────────────────────────
    # Tick quotidien (appelé par APScheduler à minuit UTC)
    # ─────────────────────────────────────────────────────

    async def daily_tick(self) -> None:
        """
        Traitement quotidien pour tous les plans warmup actifs.
        Appelé automatiquement par le scheduler à 00:05 UTC.
        """
        plans = (
            self.db.query(WarmupPlan)
            .filter(WarmupPlan.phase.notin_(["completed", "emergency_stop"]))
            .all()
        )

        resumed = 0
        advanced = 0

        for plan in plans:
            # 1. Tenter de reprendre les plans en pause
            if plan.paused:
                if await self.resume_paused_plan(plan):
                    resumed += 1
                continue

            # 2. Avancer au jour suivant
            if await self.advance_day(plan):
                advanced += 1

        logger.info(
            "warmup_daily_tick",
            total_plans=len(plans),
            resumed=resumed,
            advanced=advanced,
        )

    # ─────────────────────────────────────────────────────
    # Utilitaires
    # ─────────────────────────────────────────────────────

    def get_status(self, plan: WarmupPlan) -> dict:
        """Retourne un résumé complet de l'état d'un plan warmup."""
        day_number = self._get_day_number(plan)
        bounce_7d, spam_7d = self._compute_rates(plan, days=7)
        bounce_24h, spam_24h = self._compute_24h_rates(plan)
        days_remaining = max(0, WARMUP_TOTAL_DAYS - day_number)

        return {
            "phase": plan.phase,
            "day_number": day_number,
            "days_remaining": days_remaining,
            "current_daily_quota": plan.current_daily_quota,
            "hourly_quota": daily_to_hourly_quota(plan.current_daily_quota),
            "paused": plan.paused,
            "pause_until": plan.pause_until.isoformat() if plan.pause_until else None,
            "bounce_rate_7d": bounce_7d,
            "spam_rate_7d": spam_7d,
            "bounce_rate_24h": bounce_24h,
            "spam_rate_24h": spam_24h,
            "thresholds": {
                "max_bounce": settings.WARMUP_MAX_BOUNCE_RATE,
                "max_spam": settings.WARMUP_MAX_SPAM_RATE,
                "emergency_bounce": settings.WARMUP_EMERGENCY_BOUNCE_RATE,
                "emergency_spam": settings.WARMUP_EMERGENCY_SPAM_RATE,
            },
            "quota_schedule": {
                f"day_{i+1}": q
                for i, q in enumerate(DAILY_QUOTAS)
            },
        }
