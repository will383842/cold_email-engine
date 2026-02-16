#!/usr/bin/env python3
"""Verification script for Phase 2 implementation."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

print("="*80)
print("EMAIL ENGINE - PHASE 2 VERIFICATION")
print("="*80)

errors = []

# 1. Domain Services
print("\n1. Checking domain services...")
try:
    from src.domain.services import TemplateSelector, ContactValidator
    print("   OK - TemplateSelector imported")
    print("   OK - ContactValidator imported")

    # Test ContactValidator
    validator = ContactValidator()
    from app.enums import ValidationStatus
    status, score, errs = validator.validate("test@example.com")
    assert status == ValidationStatus.VALID
    assert score >= 0.8
    print("   OK - ContactValidator.validate() works")

except Exception as e:
    errors.append(f"Domain services: {e}")
    print(f"   ERROR: {e}")

# 2. Template Repository
print("\n2. Checking template repository...")
try:
    from src.domain.repositories import ITemplateRepository
    from src.infrastructure.persistence import SQLAlchemyTemplateRepository
    from abc import ABC

    assert issubclass(ITemplateRepository, ABC)
    assert issubclass(SQLAlchemyTemplateRepository, ITemplateRepository)

    print("   OK - ITemplateRepository is abstract")
    print("   OK - SQLAlchemyTemplateRepository implements interface")

except Exception as e:
    errors.append(f"Template repository: {e}")
    print(f"   ERROR: {e}")

# 3. External Services
print("\n3. Checking external services...")
try:
    from src.infrastructure.external import MailWizzClient, PowerMTAConfigGenerator

    # Test MailWizzClient
    client = MailWizzClient(
        base_url="https://test.example.com",
        public_key="test-public",
        private_key="test-private"
    )
    assert client.base_url == "https://test.example.com"
    print("   OK - MailWizzClient initialized")

    # Test PowerMTAConfigGenerator
    generator = PowerMTAConfigGenerator()
    config = generator.generate_vmta_pool(
        pool_name="test-pool",
        ips=[
            {"address": "1.2.3.4", "hostname": "mail1.test.com", "vmta_name": "vmta-1", "weight": 100}
        ]
    )
    assert "test-pool" in config
    assert "vmta-1" in config
    print("   OK - PowerMTAConfigGenerator.generate_vmta_pool() works")

except Exception as e:
    errors.append(f"External services: {e}")
    print(f"   ERROR: {e}")

# 4. Background Jobs
print("\n4. Checking background jobs...")
try:
    from src.infrastructure.background import celery_app
    from src.infrastructure.background import (
        validate_contact_task,
        inject_contact_to_mailwizz_task,
        send_campaign_task,
        advance_warmup_task
    )

    assert celery_app.broker_url == "redis://localhost:6379/0"
    print("   OK - Celery app configured")
    print("   OK - validate_contact_task imported")
    print("   OK - inject_contact_to_mailwizz_task imported")
    print("   OK - send_campaign_task imported")
    print("   OK - advance_warmup_task imported")

except Exception as e:
    errors.append(f"Background jobs: {e}")
    print(f"   ERROR: {e}")

# 5. API v2 Templates
print("\n5. Checking API v2 templates...")
try:
    from src.presentation.api.v2 import router

    # Check routes registered
    routes = [route.path for route in router.routes]
    assert any("/contacts" in route for route in routes)
    assert any("/templates" in route for route in routes)

    print("   OK - API v2 router includes contacts")
    print("   OK - API v2 router includes templates")

except Exception as e:
    errors.append(f"API v2 templates: {e}")
    print(f"   ERROR: {e}")

# 6. Template Selector Logic
print("\n6. Checking template selector logic...")
try:
    from src.domain.services import TemplateSelector

    # Mock repo for testing
    class MockTemplateRepo:
        def find_by_language_and_category(self, tenant_id, language, category):
            # Simulate template not found
            return None

        def find_default(self, tenant_id, language):
            return None

    selector = TemplateSelector(MockTemplateRepo())

    # Test selection (should return None for mock)
    result = selector.select(tenant_id=1, language="fr", category="avocat")
    assert result is None  # Expected since mock returns None

    print("   OK - TemplateSelector.select() works")

    # Test render
    template = {
        "subject": "Hello {firstName}",
        "body_html": "<p>Dear {firstName},</p>"
    }
    variables = {"firstName": "Jean"}
    subject, body = selector.render_template(template, variables)
    assert subject == "Hello Jean"
    assert "<p>Dear Jean,</p>" in body

    print("   OK - TemplateSelector.render_template() works")

except Exception as e:
    errors.append(f"Template selector logic: {e}")
    print(f"   ERROR: {e}")

# 7. File structure
print("\n7. Checking file structure...")
try:
    # Check all files exist
    base_path = Path(__file__).parent.parent

    files_to_check = [
        "src/domain/services/template_selector.py",
        "src/domain/services/contact_validator.py",
        "src/domain/repositories/template_repository.py",
        "src/infrastructure/persistence/sqlalchemy_template_repository.py",
        "src/infrastructure/external/mailwizz_client.py",
        "src/infrastructure/external/powermta_config_generator.py",
        "src/infrastructure/background/celery_app.py",
        "src/infrastructure/background/tasks.py",
        "src/presentation/api/v2/templates.py",
        "PHASE-2-COMPLETE.md",
    ]

    missing = []
    for file_path in files_to_check:
        full_path = base_path / file_path
        if not full_path.exists():
            missing.append(file_path)

    if missing:
        errors.append(f"Missing files: {', '.join(missing)}")
        print(f"   ERROR: Missing files: {missing}")
    else:
        print(f"   OK - All {len(files_to_check)} Phase 2 files exist")

except Exception as e:
    errors.append(f"File structure: {e}")
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
    print("\nALL PHASE 2 CHECKS PASSED!")
    print("\nPhase 2 Components:")
    print("  - 2 Domain Services (TemplateSelector, ContactValidator)")
    print("  - 1 Repository Interface (ITemplateRepository)")
    print("  - 1 Repository Implementation (SQLAlchemyTemplateRepository)")
    print("  - 2 External Services (MailWizzClient, PowerMTAConfigGenerator)")
    print("  - 4 Background Jobs (Celery tasks)")
    print("  - 1 API v2 Endpoint (Templates)")
    print("\nNext steps:")
    print("  1. Install dependencies: pip install celery redis requests")
    print("  2. Start Redis: docker run -d -p 6379:6379 redis:alpine")
    print("  3. Start Celery: celery -A src.infrastructure.background.celery_app worker -l info")
    print("  4. Include API v2 in main.py")
    print("  5. Create HTML templates for 9 languages")
    sys.exit(0)
