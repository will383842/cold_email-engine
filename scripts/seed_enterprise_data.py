#!/usr/bin/env python3
"""Seed script for enterprise multi-tenant data.

Creates:
- 2 Tenants (Client 1, Client 2)
- 100 IPs (50 per tenant)
- 100 Domains (1 per IP)
- 2 MailWizz instances (1 per tenant)
- Sample tags for Client 1

Run: python scripts/seed_enterprise_data.py
"""

import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Domain, IP, MailwizzInstance, Tag, Tenant


def seed_tenants(db: Session) -> tuple[Tenant, Tenant]:
    """Create 2 tenants: Client 1 and Client 2."""
    print("Creating tenants...")

    # Client 1
    client1 = Tenant(
        slug="client-1",
        name="Client 1",
        brand_domain="client1-brand.com",
        sending_domain_base="client1-mail.com",
        is_active=True,
        created_at=datetime.utcnow(),
    )

    # Client 2
    client2 = Tenant(
        slug="client-2",
        name="Client 2",
        brand_domain="client2-brand.com",
        sending_domain_base="client2-mail.com",
        is_active=True,
        created_at=datetime.utcnow(),
    )

    db.add(client1)
    db.add(client2)
    db.commit()
    db.refresh(client1)
    db.refresh(client2)

    print(f"✓ Created tenant: {client1.name} (ID: {client1.id})")
    print(f"✓ Created tenant: {client2.name} (ID: {client2.id})")

    return client1, client2


def seed_ips_and_domains(db: Session, client1: Tenant, client2: Tenant) -> None:
    """Create 100 IPs (50 per tenant) and 100 domains (1 per IP)."""
    print("\nCreating IPs and domains...")

    # Client 1: 50 IPs (45.123.10.1-50)
    print(f"\nCreating 50 IPs for {client1.name}...")
    for i in range(1, 51):
        ip_address = f"45.123.10.{i}"
        hostname = f"mail{i}.client1-mail.com"
        domain_name = f"mail{i}.client1-mail.com"

        # Determine status and weight based on pool distribution
        if i <= 40:
            # Active pool (40 IPs)
            status = "active"
            weight = 100
        elif i <= 47:
            # Warming pool (7 IPs)
            status = "warming"
            weight = 50
        else:
            # Standby pool (3 IPs)
            status = "standby"
            weight = 0

        # Create IP
        ip = IP(
            address=ip_address,
            hostname=hostname,
            purpose="cold",
            status=status,
            weight=weight,
            vmta_name=f"vmta-client1-{i}",
            pool_name="client1-pool",
            tenant_id=client1.id,
            created_at=datetime.utcnow(),
        )
        db.add(ip)
        db.flush()  # Get IP id

        # Create Domain
        domain = Domain(
            name=domain_name,
            purpose="cold",
            ip_id=ip.id,
            dkim_selector="default",
            tenant_id=client1.id,
            created_at=datetime.utcnow(),
        )
        db.add(domain)

        if i % 10 == 0:
            print(f"  Created {i}/50 IPs for {client1.name}...")

    print(f"✓ Created 50 IPs + 50 domains for {client1.name}")

    # Client 2: 50 IPs (45.124.20.1-50)
    print(f"\nCreating 50 IPs for {client2.name}...")
    for i in range(1, 51):
        ip_address = f"45.124.20.{i}"
        hostname = f"mail{i}.client2-mail.com"
        domain_name = f"mail{i}.client2-mail.com"

        # Same pool distribution
        if i <= 40:
            status = "active"
            weight = 100
        elif i <= 47:
            status = "warming"
            weight = 50
        else:
            status = "standby"
            weight = 0

        # Create IP
        ip = IP(
            address=ip_address,
            hostname=hostname,
            purpose="cold",
            status=status,
            weight=weight,
            vmta_name=f"vmta-client2-{i}",
            pool_name="client2-pool",
            tenant_id=client2.id,
            created_at=datetime.utcnow(),
        )
        db.add(ip)
        db.flush()

        # Create Domain
        domain = Domain(
            name=domain_name,
            purpose="cold",
            ip_id=ip.id,
            dkim_selector="default",
            tenant_id=client2.id,
            created_at=datetime.utcnow(),
        )
        db.add(domain)

        if i % 10 == 0:
            print(f"  Created {i}/50 IPs for {client2.name}...")

    print(f"✓ Created 50 IPs + 50 domains for {client2.name}")
    db.commit()


def seed_mailwizz_instances(db: Session, client1: Tenant, client2: Tenant) -> None:
    """Create 2 MailWizz instances (1 per tenant)."""
    print("\nCreating MailWizz instances...")

    # Client 1 MailWizz
    client1_mailwizz = MailwizzInstance(
        tenant_id=client1.id,
        name="MailWizz Client 1",
        base_url="https://mailwizz-client1.example.com",
        api_public_key="REPLACE_WITH_REAL_KEY",
        api_private_key="REPLACE_WITH_REAL_KEY",
        default_list_id=1,
        is_active=True,
        created_at=datetime.utcnow(),
    )

    # Client 2 MailWizz
    client2_mailwizz = MailwizzInstance(
        tenant_id=client2.id,
        name="MailWizz Client 2",
        base_url="https://mailwizz-client2.example.com",
        api_public_key="REPLACE_WITH_REAL_KEY",
        api_private_key="REPLACE_WITH_REAL_KEY",
        default_list_id=1,
        is_active=True,
        created_at=datetime.utcnow(),
    )

    db.add(client1_mailwizz)
    db.add(client2_mailwizz)
    db.commit()

    print(f"✓ Created MailWizz instance for {client1.name}")
    print(f"✓ Created MailWizz instance for {client2.name}")


def seed_tags(db: Session, client1: Tenant) -> None:
    """Create sample tags for Client 1."""
    print("\nCreating sample tags for Client 1...")

    tags_data = [
        # Prestataires
        {"slug": "prestataire", "label": "Prestataire", "parent": None, "color": "#10B981"},
        {"slug": "avocat", "label": "Avocat", "parent": "prestataire", "color": "#3B82F6"},
        {"slug": "expat-aidant", "label": "Expat Aidant", "parent": "prestataire", "color": "#6366F1"},
        # Marketing Partners
        {"slug": "marketing-partner", "label": "Marketing Partner", "parent": None, "color": "#8B5CF6"},
        {"slug": "blogger", "label": "Blogueur", "parent": "marketing-partner", "color": "#A855F7"},
        {"slug": "influencer", "label": "Influenceur", "parent": "marketing-partner", "color": "#D946EF"},
        {"slug": "chatter", "label": "Chatter", "parent": "marketing-partner", "color": "#EC4899"},
        {"slug": "admin-group", "label": "Admin Group", "parent": "marketing-partner", "color": "#F43F5E"},
        # Clients
        {"slug": "client", "label": "Client", "parent": None, "color": "#F59E0B"},
        {"slug": "vacancier", "label": "Vacancier", "parent": "client", "color": "#FBBF24"},
        {"slug": "expat", "label": "Expat", "parent": "client", "color": "#FCD34D"},
        {"slug": "digital-nomad", "label": "Digital Nomad", "parent": "client", "color": "#FDE68A"},
        # Languages
        {"slug": "lang-fr", "label": "Français", "parent": None, "color": "#3B82F6"},
        {"slug": "lang-en", "label": "English", "parent": None, "color": "#3B82F6"},
        {"slug": "lang-es", "label": "Español", "parent": None, "color": "#3B82F6"},
        {"slug": "lang-de", "label": "Deutsch", "parent": None, "color": "#3B82F6"},
    ]

    # Create parent tags first
    tag_map = {}
    for tag_data in tags_data:
        if tag_data["parent"] is None:
            tag = Tag(
                tenant_id=client1.id,
                slug=tag_data["slug"],
                label=tag_data["label"],
                color=tag_data["color"],
                created_at=datetime.utcnow(),
            )
            db.add(tag)
            db.flush()
            tag_map[tag_data["slug"]] = tag.id

    # Create child tags
    for tag_data in tags_data:
        if tag_data["parent"] is not None:
            parent_id = tag_map.get(tag_data["parent"])
            tag = Tag(
                tenant_id=client1.id,
                slug=tag_data["slug"],
                label=tag_data["label"],
                parent_id=parent_id,
                color=tag_data["color"],
                created_at=datetime.utcnow(),
            )
            db.add(tag)
            db.flush()
            tag_map[tag_data["slug"]] = tag.id

    db.commit()
    print(f"✓ Created {len(tags_data)} sample tags")


def main():
    """Main seed function."""
    print("=" * 80)
    print("EMAIL ENGINE - ENTERPRISE MULTI-TENANT DATA SEED")
    print("=" * 80)

    db = SessionLocal()

    try:
        # 1. Create tenants
        client1, client2 = seed_tenants(db)

        # 2. Create IPs and domains (100 IPs, 100 domains)
        seed_ips_and_domains(db, client1, client2)

        # 3. Create MailWizz instances
        seed_mailwizz_instances(db, client1, client2)

        # 4. Create sample tags for Client 1
        seed_tags(db, client1)

        print("\n" + "=" * 80)
        print("SEED COMPLETED SUCCESSFULLY!")
        print("=" * 80)
        print("\nSummary:")
        print("  - 2 Tenants (Client 1, Client 2)")
        print("  - 100 IPs (50 per tenant)")
        print("  - 100 Domains (1 per IP)")
        print("  - 2 MailWizz instances")
        print("  - 16 sample tags (Client 1 only)")
        print("\nNext steps:")
        print("  1. Update MailWizz API keys in mailwizz_instances table")
        print("  2. Configure DNS records (SPF, DKIM, DMARC, PTR) for all 100 domains")
        print("  3. Configure PowerMTA with 100 VirtualMTAs")
        print("  4. Start IP warmup for 'warming' IPs")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
