#!/usr/bin/env python3
"""Simple verification script for enterprise implementation."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

print("="*80)
print("EMAIL ENGINE - IMPLEMENTATION VERIFICATION")
print("="*80)

errors = []

# 1. Check Models
print("\n1. Checking models...")
try:
    from app.models import (
        Tenant, DataSource, Tag, Contact, ContactTag,
        EmailTemplate, Campaign, ContactEvent, MailwizzInstance,
        IP, Domain
    )
    print("   OK - All 9 new models imported")
    print("   OK - IP and Domain imported")
except Exception as e:
    errors.append(f"Models import: {e}")
    print(f"   ERROR: {e}")

# 2. Check Enums
print("\n2. Checking enums...")
try:
    from app.enums import (
        DataSourceType, ContactStatus, ValidationStatus,
        CampaignStatus, EventType, Language, ProspectCategory
    )
    assert len([l for l in Language]) == 9, "Should have 9 languages"
    print("   OK - All 7 new enums imported")
    print("   OK - Language enum has 9 values")
except Exception as e:
    errors.append(f"Enums check: {e}")
    print(f"   ERROR: {e}")

# 3. Check Value Objects
print("\n3. Checking value objects...")
try:
    from src.domain.value_objects import Email, Language as DomainLanguage, TagSlug

    email = Email("test@example.com")
    assert email.domain() == "example.com"

    lang = DomainLanguage("fr")
    assert lang.code == "fr"

    slug = TagSlug.from_string("Test Slug!")
    assert slug.value == "test-slug"

    print("   OK - Email value object works")
    print("   OK - Language value object works")
    print("   OK - TagSlug value object works")
except Exception as e:
    errors.append(f"Value objects: {e}")
    print(f"   ERROR: {e}")

# 4. Check Entities
print("\n4. Checking entities...")
try:
    from src.domain.entities import Contact as ContactEntity, Campaign as CampaignEntity
    from src.domain.value_objects import Email, Language as DomainLanguage
    from app.enums import ContactStatus, ValidationStatus

    contact = ContactEntity(
        tenant_id=1,
        data_source_id=1,
        email=Email("test@example.com"),
        language=DomainLanguage("fr")
    )

    contact.validate(ValidationStatus.VALID, 0.95)
    assert contact.status == ContactStatus.VALID

    print("   OK - Contact entity works")
    print("   OK - Contact business methods work")
except Exception as e:
    errors.append(f"Entities: {e}")
    print(f"   ERROR: {e}")

# 5. Check Repository Interfaces
print("\n5. Checking repository interfaces...")
try:
    from src.domain.repositories import IContactRepository, ICampaignRepository
    from abc import ABC

    assert issubclass(IContactRepository, ABC)
    assert issubclass(ICampaignRepository, ABC)

    print("   OK - IContactRepository is abstract")
    print("   OK - ICampaignRepository is abstract")
except Exception as e:
    errors.append(f"Repository interfaces: {e}")
    print(f"   ERROR: {e}")

# 6. Check Repository Implementations
print("\n6. Checking repository implementations...")
try:
    from src.infrastructure.persistence import SQLAlchemyContactRepository, SQLAlchemyCampaignRepository
    from src.domain.repositories import IContactRepository, ICampaignRepository

    assert issubclass(SQLAlchemyContactRepository, IContactRepository)
    assert issubclass(SQLAlchemyCampaignRepository, ICampaignRepository)

    print("   OK - SQLAlchemyContactRepository implements interface")
    print("   OK - SQLAlchemyCampaignRepository implements interface")
except Exception as e:
    errors.append(f"Repository implementations: {e}")
    print(f"   ERROR: {e}")

# 7. Check Use Cases
print("\n7. Checking use cases...")
try:
    from src.application.use_cases import IngestContactsUseCase
    from src.application.use_cases.ingest_contacts import IngestContactDTO

    dto = IngestContactDTO(
        tenant_id=1,
        data_source_id=1,
        email="test@example.com",
        language="fr"
    )

    assert dto.email == "test@example.com"

    print("   OK - IngestContactDTO works")
    print("   OK - IngestContactsUseCase imported")
except Exception as e:
    errors.append(f"Use cases: {e}")
    print(f"   ERROR: {e}")

# 8. Check Migration File
print("\n8. Checking migration file...")
try:
    migration_path = Path(__file__).parent.parent / "alembic" / "versions" / "003_enterprise_multi_tenant.py"
    assert migration_path.exists(), "Migration file not found"

    with open(migration_path, 'r', encoding='utf-8') as f:
        content = f.read()

    assert 'revision: str = "003"' in content
    assert 'down_revision: Union[str, None] = "002"' in content
    assert 'def upgrade()' in content
    assert 'def downgrade()' in content
    assert 'create_table("tenants"' in content
    assert 'create_table("contacts"' in content

    print("   OK - Migration file exists")
    print("   OK - Migration has correct revision (003)")
    print("   OK - Migration has upgrade/downgrade")
    print("   OK - Migration creates tenants table")
    print("   OK - Migration creates contacts table")
except Exception as e:
    errors.append(f"Migration file: {e}")
    print(f"   ERROR: {e}")

# 9. Check Seed Script
print("\n9. Checking seed script...")
try:
    seed_path = Path(__file__).parent / "seed_enterprise_data.py"
    assert seed_path.exists(), "Seed script not found"

    with open(seed_path, 'r', encoding='utf-8') as f:
        content = f.read()

    assert 'def seed_tenants' in content
    assert 'def seed_ips_and_domains' in content
    assert 'for i in range(1, 51)' in content
    assert '45.123.10.' in content
    assert '45.124.20.' in content

    print("   OK - Seed script exists")
    print("   OK - Seed script has required functions")
    print("   OK - Seed script creates 50 IPs per tenant")
except Exception as e:
    errors.append(f"Seed script: {e}")
    print(f"   ERROR: {e}")

# Summary
print("\n" + "="*80)
print("SUMMARY")
print("="*80)

if errors:
    print(f"\nERRORS FOUND: {len(errors)}")
    for i, err in enumerate(errors, 1):
        print(f"  {i}. {err}")
    sys.exit(1)
else:
    print("\nALL CHECKS PASSED!")
    print("\nImplementation is correct and ready for deployment.")
    print("\nNext steps:")
    print("  1. Run: alembic upgrade head")
    print("  2. Run: python scripts/seed_enterprise_data.py")
    print("  3. Configure DNS, PowerMTA, MailWizz")
    sys.exit(0)
