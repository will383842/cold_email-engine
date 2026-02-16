#!/usr/bin/env python3
"""
Add new domain + IP to tenant and start warmup.

This script allows progressive scaling from 5 domains to 50+ domains.

Usage:
    python scripts/add_domain.py --tenant 1 --domain mail6.sos-mail.com --ip 45.123.10.6
    python scripts/add_domain.py --tenant 2 --domain mail6.ulixai-mail.com --ip 45.124.20.6 --dry-run

Arguments:
    --tenant: Tenant ID (1=SOS-Expat, 2=Ulixai)
    --domain: Domain name (e.g., mail6.sos-mail.com)
    --ip: IP address (e.g., 45.123.10.6)
    --dry-run: Preview without creating (optional)

Example Workflow:
    Week 1-5: Create 5 initial domains (1 per week)
    Week 6+: First IPs start becoming ACTIVE
    Week 7+: Add 1 new domain per week maximum

Warmup Schedule:
    Week 1: 50 emails/day
    Week 2: 200 emails/day
    Week 3: 500 emails/day
    Week 4: 1,500 emails/day
    Week 5: 5,000 emails/day
    Week 6: 10,000 emails/day → ACTIVE
"""

import argparse
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, ".")

from app.database import SessionLocal
from app.models import Domain, IP, Tenant
from app.enums import DomainStatus, IPStatus
from app.services.warmup_engine import WarmupEngine


def validate_args(args):
    """Validate command-line arguments."""
    errors = []

    # Validate tenant
    if args.tenant not in [1, 2]:
        errors.append(f"Invalid tenant ID: {args.tenant}. Must be 1 (SOS-Expat) or 2 (Ulixai)")

    # Validate domain format
    if not args.domain or "." not in args.domain:
        errors.append(f"Invalid domain format: {args.domain}")

    # Validate IP format
    ip_parts = args.ip.split(".")
    if len(ip_parts) != 4:
        errors.append(f"Invalid IP format: {args.ip}")
    else:
        try:
            for part in ip_parts:
                num = int(part)
                if num < 0 or num > 255:
                    errors.append(f"Invalid IP octet: {part}")
        except ValueError:
            errors.append(f"Invalid IP format: {args.ip}")

    return errors


def check_duplicates(db, tenant_id, domain_name, ip_address):
    """Check for duplicate domain or IP."""
    existing_domain = db.query(Domain).filter(
        Domain.tenant_id == tenant_id,
        Domain.domain == domain_name
    ).first()

    existing_ip = db.query(IP).filter(
        IP.tenant_id == tenant_id,
        IP.address == ip_address
    ).first()

    return existing_domain, existing_ip


def add_domain_with_ip(tenant_id: int, domain_name: str, ip_address: str, dry_run: bool = False):
    """
    Add a new domain + IP and start warmup.

    Args:
        tenant_id: Tenant ID (1 or 2)
        domain_name: Domain name
        ip_address: IP address
        dry_run: If True, preview without creating

    Returns:
        bool: Success status
    """
    db = SessionLocal()
    try:
        # Validate tenant exists
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            print(f"❌ Error: Tenant {tenant_id} not found")
            return False

        print(f"\n{'='*60}")
        print(f"Adding Domain + IP for {tenant.name}")
        print(f"{'='*60}\n")

        # Check for duplicates
        existing_domain, existing_ip = check_duplicates(db, tenant_id, domain_name, ip_address)

        if existing_domain:
            print(f"❌ Error: Domain {domain_name} already exists (ID: {existing_domain.id})")
            return False

        if existing_ip:
            print(f"❌ Error: IP {ip_address} already exists (ID: {existing_ip.id})")
            return False

        # Get current count
        domain_count = db.query(Domain).filter(Domain.tenant_id == tenant_id).count()
        ip_count = db.query(IP).filter(IP.tenant_id == tenant_id).count()

        print(f"Current Status:")
        print(f"  - Domains: {domain_count}")
        print(f"  - IPs: {ip_count}\n")

        if dry_run:
            print("🔍 DRY RUN MODE - No changes will be made\n")
            print(f"Would create:")
            print(f"  Domain: {domain_name}")
            print(f"  IP: {ip_address}")
            print(f"  Status: WARMING")
            print(f"  Initial Quota: 50 emails/day")
            print(f"  Target Quota: 10,000 emails/day (in 6 weeks)\n")
            return True

        # Create domain
        print(f"Creating domain: {domain_name}...")
        domain = Domain(
            tenant_id=tenant_id,
            domain=domain_name,
            status=DomainStatus.WARMING.value,
            created_at=datetime.utcnow(),
        )
        db.add(domain)
        db.flush()
        print(f"  ✅ Domain created (ID: {domain.id})\n")

        # Create IP
        print(f"Creating IP: {ip_address}...")
        ip = IP(
            tenant_id=tenant_id,
            address=ip_address,
            domain_id=domain.id,
            status=IPStatus.WARMING.value,
            weight=0,  # Will be 100 after warmup completion
            created_at=datetime.utcnow(),
        )
        db.add(ip)
        db.flush()
        print(f"  ✅ IP created (ID: {ip.id})\n")

        # Create warmup plan
        print(f"Creating warmup plan...")
        engine = WarmupEngine(db)
        plan = engine.create_plan(ip)
        print(f"  ✅ Warmup plan created (ID: {plan.id})\n")

        # Commit all changes
        db.commit()

        # Print summary
        print(f"{'='*60}")
        print(f"✅ SUCCESS - Domain + IP created and warmup started")
        print(f"{'='*60}\n")

        print(f"Details:")
        print(f"  Domain: {domain_name} (ID: {domain.id})")
        print(f"  IP: {ip_address} (ID: {ip.id})")
        print(f"  Status: {ip.status}")
        print(f"  Warmup Phase: {plan.phase}")
        print(f"  Daily Quota: {plan.current_daily_quota} emails/day")
        print(f"  Target: {plan.target_daily_quota} emails/day (in ~42 days)")
        print(f"  Started: {plan.started_at.strftime('%Y-%m-%d %H:%M UTC')}\n")

        print(f"New Totals:")
        print(f"  - Domains: {domain_count + 1}")
        print(f"  - IPs: {ip_count + 1}\n")

        print(f"Next Steps:")
        print(f"  1. Configure DNS records for {domain_name}")
        print(f"  2. Add DKIM/SPF/DMARC records")
        print(f"  3. Configure PowerMTA VirtualMTA for {ip_address}")
        print(f"  4. Start sending at {plan.current_daily_quota} emails/day")
        print(f"  5. Monitor warmup progress: curl http://localhost:8000/api/v1/warmup")
        print(f"  6. Wait 7 days before adding next domain\n")

        return True

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Add new domain + IP to tenant and start warmup",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Add 6th domain for SOS-Expat
  python scripts/add_domain.py --tenant 1 --domain mail6.sos-mail.com --ip 45.123.10.6

  # Add 6th domain for Ulixai
  python scripts/add_domain.py --tenant 2 --domain mail6.ulixai-mail.com --ip 45.124.20.6

  # Dry run (preview without creating)
  python scripts/add_domain.py --tenant 1 --domain mail6.sos-mail.com --ip 45.123.10.6 --dry-run

Recommended Schedule:
  Week 1: Create mail1.sos-mail.com + 45.123.10.1
  Week 2: Create mail2.sos-mail.com + 45.123.10.2
  Week 3: Create mail3.sos-mail.com + 45.123.10.3
  Week 4: Create mail4.sos-mail.com + 45.123.10.4
  Week 5: Create mail5.sos-mail.com + 45.123.10.5
  Week 6: First IP becomes ACTIVE (10,000/day)
  Week 7+: Add 1 new domain per week maximum
        """
    )

    parser.add_argument(
        "--tenant",
        type=int,
        required=True,
        choices=[1, 2],
        help="Tenant ID: 1 (SOS-Expat) or 2 (Ulixai)"
    )
    parser.add_argument(
        "--domain",
        type=str,
        required=True,
        help="Domain name (e.g., mail6.sos-mail.com)"
    )
    parser.add_argument(
        "--ip",
        type=str,
        required=True,
        help="IP address (e.g., 45.123.10.6)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview without creating"
    )

    args = parser.parse_args()

    # Validate arguments
    errors = validate_args(args)
    if errors:
        print("\n❌ Validation Errors:")
        for error in errors:
            print(f"  - {error}")
        print()
        sys.exit(1)

    # Execute
    success = add_domain_with_ip(
        tenant_id=args.tenant,
        domain_name=args.domain,
        ip_address=args.ip,
        dry_run=args.dry_run
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
