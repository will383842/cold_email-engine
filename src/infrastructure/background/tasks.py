"""Celery background tasks."""

from .celery_app import celery_app


@celery_app.task(name="src.infrastructure.background.tasks.validate_contact_task")
def validate_contact_task(contact_id: int) -> dict:
    """
    Validate contact email address (background task).

    Args:
        contact_id: Contact ID to validate

    Returns:
        Dict with validation results

    Flow:
        1. Fetch contact from database
        2. Run ContactValidator.validate()
        3. Update contact with validation_status, validation_score, validation_errors
        4. Save to database

    Example:
        validate_contact_task.delay(contact_id=123)
    """
    from app.database import SessionLocal
    from app.models import Contact
    from src.domain.services import ContactValidator

    db = SessionLocal()
    try:
        # Fetch contact
        contact = db.query(Contact).filter_by(id=contact_id).first()
        if not contact:
            return {"success": False, "error": f"Contact {contact_id} not found"}

        # Validate
        validator = ContactValidator()
        status, score, errors = validator.validate(contact.email)

        # Update contact
        contact.validation_status = status.value
        contact.validation_score = score

        import json
        contact.validation_errors = json.dumps(errors)

        # Update status based on validation
        if status.value == "valid":
            contact.status = "valid"
        elif status.value == "invalid":
            contact.status = "invalid"

        db.commit()

        return {
            "success": True,
            "contact_id": contact_id,
            "email": contact.email,
            "status": status.value,
            "score": score,
            "errors": errors,
        }

    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}
    finally:
        db.close()


@celery_app.task(name="src.infrastructure.background.tasks.inject_contact_to_mailwizz_task")
def inject_contact_to_mailwizz_task(contact_id: int) -> dict:
    """
    Inject contact into MailWizz (background task).

    Args:
        contact_id: Contact ID to inject

    Returns:
        Dict with injection results

    Flow:
        1. Fetch contact + tenant + mailwizz_instance
        2. Create subscriber in MailWizz
        3. Update contact.mailwizz_subscriber_id
        4. Save to database

    Example:
        inject_contact_to_mailwizz_task.delay(contact_id=123)
    """
    from app.database import SessionLocal
    from app.models import Contact, MailwizzInstance
    from src.infrastructure.external import MailWizzClient

    db = SessionLocal()
    try:
        # Fetch contact
        contact = db.query(Contact).filter_by(id=contact_id).first()
        if not contact:
            return {"success": False, "error": f"Contact {contact_id} not found"}

        # Check if already injected
        if contact.mailwizz_subscriber_id:
            return {
                "success": True,
                "message": "Already injected",
                "subscriber_id": contact.mailwizz_subscriber_id,
            }

        # Fetch MailWizz instance for tenant
        mailwizz = db.query(MailwizzInstance).filter_by(tenant_id=contact.tenant_id).first()
        if not mailwizz:
            return {"success": False, "error": "MailWizz instance not found for tenant"}

        # Create MailWizz client
        client = MailWizzClient(
            base_url=mailwizz.base_url,
            public_key=mailwizz.api_public_key,
            private_key=mailwizz.api_private_key,
        )

        # Prepare subscriber data
        subscriber_data = {
            "EMAIL": contact.email,
        }
        if contact.first_name:
            subscriber_data["FNAME"] = contact.first_name
        if contact.last_name:
            subscriber_data["LNAME"] = contact.last_name
        if contact.company:
            subscriber_data["COMPANY"] = contact.company
        if contact.website:
            subscriber_data["WEBSITE"] = contact.website

        # Create subscriber
        list_id = str(mailwizz.default_list_id)
        result = client.create_subscriber(list_id=list_id, subscriber=subscriber_data)

        # Update contact
        contact.mailwizz_subscriber_id = result.get("subscriber_uid")
        contact.mailwizz_list_id = mailwizz.default_list_id
        db.commit()

        return {
            "success": True,
            "contact_id": contact_id,
            "subscriber_id": contact.mailwizz_subscriber_id,
        }

    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}
    finally:
        db.close()


@celery_app.task(name="src.infrastructure.background.tasks.send_campaign_task")
def send_campaign_task(campaign_id: int) -> dict:
    """
    Send campaign via MailWizz with quota enforcement (background task).

    Args:
        campaign_id: Campaign ID to send

    Returns:
        Dict with send results

    Flow:
        1. Fetch campaign + template
        2. Get contacts (filtered by tags if specified)
        3. CHECK QUOTAS - CRITICAL for warmup
        4. Select IP with available quota
        5. Render template with variables
        6. Create MailWizz campaign
        7. Send campaign
        8. Reserve quota (increment counter)
        9. Update campaign.status = "sending"

    Example:
        send_campaign_task.delay(campaign_id=456)
    """
    from datetime import datetime
    from app.database import SessionLocal
    from app.models import Campaign, MailwizzInstance, Contact, EmailTemplate, IP
    from src.infrastructure.external import MailWizzClient
    from src.domain.services import QuotaChecker

    db = SessionLocal()
    try:
        # =====================================================================
        # 1. Fetch Campaign
        # =====================================================================
        campaign = db.query(Campaign).filter_by(id=campaign_id).first()
        if not campaign:
            return {"success": False, "error": f"Campaign {campaign_id} not found"}

        # =====================================================================
        # 2. Get Contacts (TODO: Filter by tags when implemented)
        # =====================================================================
        # For now, get total_recipients from campaign
        # In future: query Contact table with tag filtering
        total_recipients = campaign.total_recipients

        if total_recipients == 0:
            return {"success": False, "error": "No recipients for this campaign"}

        # =====================================================================
        # 3. CHECK QUOTAS - CRITICAL FOR WARMUP
        # =====================================================================
        quota_checker = QuotaChecker(db)

        # Get available IPs for this tenant that can send
        available_ips = quota_checker.get_available_ips_for_sending(
            tenant_id=campaign.tenant_id,
            emails_to_send=total_recipients
        )

        if not available_ips:
            return {
                "success": False,
                "error": f"No IPs available with sufficient quota to send {total_recipients} emails",
                "total_recipients": total_recipients,
            }

        # Use the IP with most remaining quota
        selected_ip = available_ips[0]

        # =====================================================================
        # 4. Reserve Quota (before sending)
        # =====================================================================
        quota_reserved = quota_checker.reserve_quota(
            ip_id=selected_ip["ip_id"],
            email_count=total_recipients
        )

        if not quota_reserved:
            return {
                "success": False,
                "error": "Failed to reserve quota (possible race condition)",
            }

        # =====================================================================
        # 5. Fetch MailWizz Instance
        # =====================================================================
        mailwizz = db.query(MailwizzInstance).filter_by(tenant_id=campaign.tenant_id).first()
        if not mailwizz:
            return {"success": False, "error": "MailWizz instance not found"}

        # Create MailWizz client
        client = MailWizzClient(
            base_url=mailwizz.base_url,
            public_key=mailwizz.api_public_key,
            private_key=mailwizz.api_private_key,
        )

        # =====================================================================
        # 6. Fetch Template & Render with Variables
        # =====================================================================
        from src.domain.services import TemplateRenderer

        renderer = TemplateRenderer()

        # Default variables for rendering
        # TODO: Get from contact when implementing contact filtering
        default_variables = {
            "first_name": "[FNAME]",  # MailWizz will replace these
            "last_name": "[LNAME]",
            "email": "[EMAIL]",
            "company": "[COMPANY]",
        }

        if campaign.template_id:
            template = db.query(EmailTemplate).filter_by(id=campaign.template_id).first()
            if template:
                # Render subject
                subject = renderer.render_subject(template.subject, default_variables)

                # Render HTML body
                html_content = renderer.render(template.body_html, default_variables)

                # Render plain text if exists
                plain_content = None
                if template.body_text:
                    plain_content = renderer.render(template.body_text, default_variables)
            else:
                subject = campaign.name
                html_content = "<p>Hello [FNAME]!</p>"
                plain_content = None
        else:
            # Fallback - use campaign name as subject
            subject = campaign.name
            html_content = "<p>Hello [FNAME]!</p>"
            plain_content = None

        # =====================================================================
        # 7. Create Campaign in MailWizz
        # =====================================================================
        # Determine from_email based on tenant
        if campaign.tenant_id == 1:  # SOS-Expat
            from_name = "SOS Expat"
            from_email = "contact@sos-expat.com"
            reply_to = "contact@sos-expat.com"
        elif campaign.tenant_id == 2:  # Ulixai
            from_name = "Ulixai"
            from_email = "contact@ulixai.com"
            reply_to = "contact@ulixai.com"
        else:
            from_name = "Email Engine"
            from_email = f"contact@tenant{campaign.tenant_id}.com"
            reply_to = from_email

        mw_campaign = client.create_campaign(
            list_id=str(mailwizz.default_list_id),
            name=campaign.name,
            subject=subject,
            from_name=from_name,
            from_email=from_email,
            reply_to=reply_to,
            html_content=html_content,
            plain_content=plain_content,  # Include plain text version
        )

        campaign.mailwizz_campaign_id = mw_campaign.get("campaign_uid")

        # =====================================================================
        # 8. Send Campaign
        # =====================================================================
        success = client.send_campaign(campaign.mailwizz_campaign_id)

        if success:
            campaign.status = "sending"
            campaign.started_at = datetime.utcnow()

        db.commit()

        return {
            "success": success,
            "campaign_id": campaign_id,
            "mailwizz_campaign_id": campaign.mailwizz_campaign_id,
            "total_recipients": total_recipients,
            "ip_used": selected_ip["address"],
            "ip_status": selected_ip["status"],
            "quota_info": {
                "daily_quota": selected_ip.get("daily_quota"),
                "sent_today_before": selected_ip.get("sent_today"),
                "remaining_after": selected_ip.get("after_send"),
            }
        }

    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}
    finally:
        db.close()


@celery_app.task(name="src.infrastructure.background.tasks.advance_warmup_task")
def advance_warmup_task() -> dict:
    """
    Advance IP warmup using professional WarmupEngine (periodic task - daily).

    Returns:
        Dict with advancement results

    Flow:
        1. Create WarmupEngine instance
        2. Call daily_tick() to process all warming IPs
        3. Engine handles:
           - Unpause IPs if pause period expired
           - Check safety thresholds (bounce/spam rates)
           - Advance phases after 7 days if safe
           - Update quotas based on phase
           - Mark IPs as ACTIVE when warmup completed
           - Send Telegram alerts

    Example:
        # Triggered by Celery Beat every 24 hours at 1:00 AM
        advance_warmup_task.delay()
    """
    import asyncio
    from app.database import SessionLocal
    from app.services.warmup_engine import WarmupEngine

    db = SessionLocal()
    try:
        # Create professional warmup engine
        engine = WarmupEngine(db)

        # Run daily tick (async - handles all warming IPs)
        # This uses asyncio because WarmupEngine.daily_tick is async
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(engine.daily_tick())
        loop.close()

        # Count results
        from app.models import IP
        warming_count = db.query(IP).filter_by(status="warming").count()
        active_count = db.query(IP).filter_by(status="active").count()

        return {
            "success": True,
            "message": "Warmup daily tick completed",
            "warming_ips": warming_count,
            "active_ips": active_count,
        }

    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}
    finally:
        db.close()

@celery_app.task(name="src.infrastructure.background.tasks.consolidate_warmup_stats_task")
def consolidate_warmup_stats_task() -> dict:
    """
    Consolidate Redis warmup counters to PostgreSQL (runs daily at 00:30).

    Reads all warmup:ip:{id}:date:{date}:* keys from Redis and saves to WarmupDailyStat.
    This allows real-time tracking via Redis while maintaining historical data in PostgreSQL.

    Returns:
        Dict with consolidation results

    Flow:
        1. Get all warming IPs from database
        2. For each IP, read yesterday's stats from Redis
        3. Save to WarmupDailyStat table
        4. Delete Redis keys after successful save

    Example:
        # Triggered by Celery Beat every day at 00:30
        consolidate_warmup_stats_task.delay()

    Redis Keys Format:
        warmup:ip:{ip_id}:date:{YYYY-MM-DD}:sent
        warmup:ip:{ip_id}:date:{YYYY-MM-DD}:delivered
        warmup:ip:{ip_id}:date:{YYYY-MM-DD}:bounced
        warmup:ip:{ip_id}:date:{YYYY-MM-DD}:complaints
        warmup:ip:{ip_id}:date:{YYYY-MM-DD}:opens
        warmup:ip:{ip_id}:date:{YYYY-MM-DD}:clicks
    """
    from datetime import datetime, timedelta
    from app.database import SessionLocal
    from app.models import IP, WarmupDailyStat
    from app.services.warmup_engine import WarmupEngine
    from src.infrastructure.cache import get_cache

    db = SessionLocal()
    cache = get_cache()

    try:
        # Get all warming IPs (including recently completed)
        warming_ips = db.query(IP).filter(
            IP.status.in_(["warming", "active"])
        ).all()

        # We consolidate yesterday's data (gives time for all events to arrive)
        yesterday = (datetime.utcnow() - timedelta(days=1)).date().isoformat()

        consolidated_count = 0
        skipped_count = 0

        for ip in warming_ips:
            if not ip.warmup_plan:
                skipped_count += 1
                continue

            # Check if already consolidated for yesterday
            existing = db.query(WarmupDailyStat).filter(
                WarmupDailyStat.plan_id == ip.warmup_plan.id,
                WarmupDailyStat.date == yesterday
            ).first()

            if existing:
                # Already consolidated, skip
                skipped_count += 1
                continue

            key_prefix = f"warmup:ip:{ip.id}:date:{yesterday}"

            # Read counters from Redis
            sent = int(cache.get(f"{key_prefix}:sent") or 0)
            delivered = int(cache.get(f"{key_prefix}:delivered") or 0)
            bounced = int(cache.get(f"{key_prefix}:bounced") or 0)
            complaints = int(cache.get(f"{key_prefix}:complaints") or 0)
            opens = int(cache.get(f"{key_prefix}:opens") or 0)
            clicks = int(cache.get(f"{key_prefix}:clicks") or 0)

            # Only record if there was activity
            if sent > 0:
                engine = WarmupEngine(db)
                stat = engine.record_daily_stats(
                    plan=ip.warmup_plan,
                    sent=sent,
                    delivered=delivered,
                    bounced=bounced,
                    complaints=complaints,
                    opens=opens,
                    clicks=clicks,
                )

                # Delete Redis keys after successful consolidation
                cache.delete(f"{key_prefix}:sent")
                cache.delete(f"{key_prefix}:delivered")
                cache.delete(f"{key_prefix}:bounced")
                cache.delete(f"{key_prefix}:complaints")
                cache.delete(f"{key_prefix}:opens")
                cache.delete(f"{key_prefix}:clicks")

                consolidated_count += 1

        return {
            "success": True,
            "date": yesterday,
            "consolidated": consolidated_count,
            "skipped": skipped_count,
            "total_warming_ips": len(warming_ips),
        }

    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}
    finally:
        db.close()


@celery_app.task(name="src.infrastructure.background.tasks.record_warmup_stats_task")
def record_warmup_stats_task(ip_id: int, stats: dict) -> dict:
    """
    Record daily warmup stats for an IP (alternative to Redis consolidation).

    This is a direct recording method if you prefer to bypass Redis.
    For production, we recommend using Redis counters + consolidation instead.

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

    Returns:
        Dict with record results

    Example:
        record_warmup_stats_task.delay(
            ip_id=1,
            stats={
                "sent": 50,
                "delivered": 48,
                "bounced": 2,
                "complaints": 0,
                "opens": 25,
                "clicks": 10
            }
        )
    """
    from app.database import SessionLocal
    from app.models import IP
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

        return {"success": True, "stat_id": stat.id, "ip": ip.address}

    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}
    finally:
        db.close()
