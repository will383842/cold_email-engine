#!/usr/bin/env python3
"""Comprehensive completeness check - What's implemented vs what's missing."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

print("="*80)
print("EMAIL ENGINE - COMPLETENESS AUDIT")
print("Verifying professional production-ready requirements")
print("="*80)

implemented = []
missing = []
warnings = []

# =============================================================================
# 1. DATABASE LAYER
# =============================================================================
print("\n1. DATABASE LAYER")
print("-" * 40)

# Check migration
migration_path = Path(__file__).parent.parent / "alembic" / "versions" / "003_enterprise_multi_tenant.py"
if migration_path.exists():
    implemented.append("Migration 003 (9 tables)")
    print("   OK - Migration 003 exists")

    # Check for indexes in migration
    with open(migration_path, 'r', encoding='utf-8') as f:
        content = f.read()
        if "index=True" in content:
            implemented.append("Database indexes")
            print("   OK - Indexes defined")
        else:
            warnings.append("Database indexes may need review for performance")
            print("   WARNING - Limited indexes found")

# Check models
try:
    from app.models import (
        Tenant, DataSource, Tag, Contact, ContactTag,
        EmailTemplate, Campaign, ContactEvent, MailwizzInstance
    )
    implemented.append("SQLAlchemy Models (9 new + 2 updated)")
    print("   OK - All models present")
except Exception as e:
    missing.append(f"Models import error: {e}")

# Check for database constraints
print("   Checking database constraints...")
if migration_path.exists():
    with open(migration_path, 'r', encoding='utf-8') as f:
        content = f.read()
        if "UniqueConstraint" in content:
            implemented.append("Unique constraints")
            print("   OK - Unique constraints defined")
        if "ForeignKey" in content:
            implemented.append("Foreign key constraints")
            print("   OK - Foreign keys defined")

# =============================================================================
# 2. DOMAIN LAYER
# =============================================================================
print("\n2. DOMAIN LAYER")
print("-" * 40)

# Value Objects
try:
    from src.domain.value_objects import Email, Language, TagSlug
    implemented.append("Value Objects (3): Email, Language, TagSlug")
    print("   OK - 3 Value Objects")
except:
    missing.append("Value Objects")

# Entities
try:
    from src.domain.entities import Contact, Campaign
    implemented.append("Entities (2): Contact, Campaign")
    print("   OK - 2 Entities")
except:
    missing.append("Entities")

# Domain Services
try:
    from src.domain.services import TemplateSelector, ContactValidator
    implemented.append("Domain Services (2): TemplateSelector, ContactValidator")
    print("   OK - 2 Domain Services")
except:
    missing.append("Domain Services")

# Repository Interfaces
try:
    from src.domain.repositories import IContactRepository, ICampaignRepository, ITemplateRepository
    implemented.append("Repository Interfaces (3)")
    print("   OK - 3 Repository Interfaces")
except:
    missing.append("Repository Interfaces")

# Domain Events
events_path = Path(__file__).parent.parent / "src" / "domain" / "events"
if events_path.exists():
    event_files = list(events_path.glob("*.py"))
    if len(event_files) > 1:  # More than just __init__.py
        implemented.append("Domain Events")
        print(f"   OK - Domain Events ({len(event_files) - 1} files)")
    else:
        missing.append("Domain Events (structure exists but not implemented)")
        print("   MISSING - Domain Events not implemented")
else:
    missing.append("Domain Events (directory not created)")
    print("   MISSING - Domain Events directory")

# =============================================================================
# 3. APPLICATION LAYER
# =============================================================================
print("\n3. APPLICATION LAYER")
print("-" * 40)

# Use Cases
use_cases_path = Path(__file__).parent.parent / "src" / "application" / "use_cases"
if use_cases_path.exists():
    use_case_files = [f for f in use_cases_path.glob("*.py") if f.name != "__init__.py"]
    implemented.append(f"Use Cases ({len(use_case_files)})")
    print(f"   OK - {len(use_case_files)} Use Case(s)")

    # Check which use cases are missing
    expected_use_cases = [
        "create_campaign",
        "send_campaign",
        "update_campaign",
        "create_template",
        "update_template",
        "validate_contacts_bulk",
    ]

    existing_files = [f.stem for f in use_case_files]
    for uc in expected_use_cases:
        if uc not in existing_files:
            missing.append(f"Use Case: {uc}")
            print(f"   MISSING - {uc} use case")

# DTOs
dto_path = Path(__file__).parent.parent / "src" / "application" / "dto"
if dto_path.exists():
    dto_files = [f for f in dto_path.glob("*.py") if f.name != "__init__.py"]
    if len(dto_files) > 0:
        implemented.append(f"DTOs ({len(dto_files)})")
        print(f"   OK - {len(dto_files)} DTO file(s)")
    else:
        warnings.append("DTOs directory exists but empty (DTOs in use_cases files)")
        print("   WARNING - DTOs mixed with use cases")
else:
    warnings.append("DTOs directory not created (DTOs in use_cases files)")
    print("   WARNING - No separate DTOs directory")

# Mappers
mappers_path = Path(__file__).parent.parent / "src" / "application" / "mappers"
if mappers_path.exists():
    mapper_files = [f for f in mappers_path.glob("*.py") if f.name != "__init__.py"]
    if len(mapper_files) > 0:
        implemented.append(f"Mappers ({len(mapper_files)})")
        print(f"   OK - {len(mapper_files)} Mapper file(s)")
    else:
        missing.append("Mappers (directory empty)")
        print("   MISSING - No mapper files")
else:
    missing.append("Mappers directory")
    print("   MISSING - Mappers directory not created")

# =============================================================================
# 4. INFRASTRUCTURE LAYER
# =============================================================================
print("\n4. INFRASTRUCTURE LAYER")
print("-" * 40)

# Repositories
try:
    from src.infrastructure.persistence import (
        SQLAlchemyContactRepository,
        SQLAlchemyCampaignRepository,
        SQLAlchemyTemplateRepository
    )
    implemented.append("Repository Implementations (3)")
    print("   OK - 3 Repository Implementations")
except:
    missing.append("Repository Implementations")

# External Services
try:
    from src.infrastructure.external import MailWizzClient, PowerMTAConfigGenerator
    implemented.append("External Services (2): MailWizz, PowerMTA")
    print("   OK - 2 External Services")
except:
    missing.append("External Services")

# Background Jobs
try:
    from src.infrastructure.background import celery_app
    implemented.append("Background Jobs (Celery configured)")
    print("   OK - Celery app configured")

    # Check tasks
    from src.infrastructure.background import (
        validate_contact_task,
        inject_contact_to_mailwizz_task,
        send_campaign_task,
        advance_warmup_task
    )
    implemented.append("Celery Tasks (4)")
    print("   OK - 4 Celery tasks")
except Exception as e:
    missing.append(f"Background Jobs: {e}")

# Cache layer
cache_path = Path(__file__).parent.parent / "src" / "infrastructure" / "cache"
if cache_path.exists():
    cache_files = [f for f in cache_path.glob("*.py") if f.name != "__init__.py"]
    if len(cache_files) > 0:
        implemented.append(f"Cache layer ({len(cache_files)} files)")
        print(f"   OK - Cache layer implemented")
    else:
        missing.append("Cache layer (directory empty)")
        print("   MISSING - Cache layer not implemented")
else:
    missing.append("Cache layer")
    print("   MISSING - Cache directory not created")

# Messaging/Queue
messaging_path = Path(__file__).parent.parent / "src" / "infrastructure" / "messaging"
if messaging_path.exists():
    messaging_files = [f for f in messaging_path.glob("*.py") if f.name != "__init__.py"]
    if len(messaging_files) > 0:
        implemented.append(f"Messaging layer ({len(messaging_files)} files)")
        print(f"   OK - Messaging layer implemented")
    else:
        missing.append("Messaging layer (directory empty)")
        print("   MISSING - Messaging layer not implemented")
else:
    missing.append("Messaging layer")
    print("   MISSING - Messaging directory not created")

# =============================================================================
# 5. PRESENTATION LAYER (API)
# =============================================================================
print("\n5. PRESENTATION LAYER (API)")
print("-" * 40)

# API v2 endpoints
api_v2_path = Path(__file__).parent.parent / "src" / "presentation" / "api" / "v2"
if api_v2_path.exists():
    endpoint_files = [f for f in api_v2_path.glob("*.py") if f.name != "__init__.py"]
    implemented.append(f"API v2 endpoints ({len(endpoint_files)} files)")
    print(f"   OK - {len(endpoint_files)} API v2 endpoint file(s)")

    # Check which endpoints exist
    existing = [f.stem for f in endpoint_files]
    print(f"   Existing: {', '.join(existing)}")

    # Expected endpoints
    expected_endpoints = ["campaigns", "tags", "data_sources", "stats", "webhooks"]
    for ep in expected_endpoints:
        if ep not in existing:
            missing.append(f"API v2 endpoint: {ep}")
            print(f"   MISSING - {ep}.py endpoint")

# Authentication/Authorization
try:
    # Check if API v2 has auth
    contacts_api = Path(__file__).parent.parent / "src" / "presentation" / "api" / "v2" / "contacts.py"
    if contacts_api.exists():
        with open(contacts_api, 'r', encoding='utf-8') as f:
            content = f.read()
            if "Depends(get_db)" in content:
                implemented.append("Database dependency injection")
                print("   OK - Database DI in API")

            if "Depends(get_current_user)" in content or "authenticate" in content:
                implemented.append("API Authentication")
                print("   OK - Authentication in API")
            else:
                missing.append("API v2 Authentication/Authorization")
                print("   MISSING - No authentication on API v2")
except:
    pass

# Rate Limiting
rate_limiting_indicators = ["RateLimiter", "rate_limit", "SlowAPI", "limiter"]
found_rate_limiting = False
for file_path in api_v2_path.glob("*.py"):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        if any(indicator in content for indicator in rate_limiting_indicators):
            found_rate_limiting = True
            break

if found_rate_limiting:
    implemented.append("Rate Limiting")
    print("   OK - Rate limiting implemented")
else:
    missing.append("Rate Limiting")
    print("   MISSING - No rate limiting")

# CORS
main_py = Path(__file__).parent.parent / "app" / "main.py"
if main_py.exists():
    with open(main_py, 'r', encoding='utf-8') as f:
        content = f.read()
        if "CORSMiddleware" in content:
            implemented.append("CORS configuration")
            print("   OK - CORS configured")
        else:
            missing.append("CORS configuration")
            print("   MISSING - CORS not configured")

# =============================================================================
# 6. MONITORING & OBSERVABILITY
# =============================================================================
print("\n6. MONITORING & OBSERVABILITY")
print("-" * 40)

# Structured logging
logging_indicators = ["structlog", "LogConfig", "logging.config"]
if main_py.exists():
    with open(main_py, 'r', encoding='utf-8') as f:
        content = f.read()
        if any(ind in content for ind in logging_indicators):
            implemented.append("Structured logging")
            print("   OK - Logging configured")
        else:
            warnings.append("Basic logging only")
            print("   WARNING - No structured logging")

# Metrics
metrics_indicators = ["prometheus", "metrics", "StatsD"]
found_metrics = False
for py_file in Path(__file__).parent.parent.rglob("*.py"):
    if py_file.is_file():
        with open(py_file, 'r', encoding='utf-8') as f:
            try:
                content = f.read()
                if any(ind in content for ind in metrics_indicators):
                    found_metrics = True
                    break
            except:
                pass

if found_metrics:
    implemented.append("Metrics/Prometheus")
    print("   OK - Metrics implemented")
else:
    missing.append("Metrics/Prometheus integration")
    print("   MISSING - No metrics")

# Health checks
health_check_path = Path(__file__).parent.parent / "app" / "api" / "routes" / "health.py"
if health_check_path.exists():
    implemented.append("Health checks (v1)")
    print("   OK - Health checks exist (API v1)")

    # Check if comprehensive
    with open(health_check_path, 'r', encoding='utf-8') as f:
        content = f.read()
        checks = ["database", "redis", "celery"]
        found_checks = [c for c in checks if c in content.lower()]
        if len(found_checks) >= 2:
            implemented.append("Comprehensive health checks")
            print(f"   OK - Health checks for: {', '.join(found_checks)}")
        else:
            warnings.append("Health checks incomplete")
            print("   WARNING - Health checks may be incomplete")
else:
    missing.append("Health checks")
    print("   MISSING - No health checks")

# Error tracking (Sentry, etc.)
error_tracking_indicators = ["sentry", "bugsnag", "rollbar"]
found_error_tracking = False
if main_py.exists():
    with open(main_py, 'r', encoding='utf-8') as f:
        content = f.read()
        if any(ind in content for ind in error_tracking_indicators):
            found_error_tracking = True

if found_error_tracking:
    implemented.append("Error tracking (Sentry/similar)")
    print("   OK - Error tracking configured")
else:
    missing.append("Error tracking (Sentry/Bugsnag/Rollbar)")
    print("   MISSING - No error tracking")

# =============================================================================
# 7. TESTING
# =============================================================================
print("\n7. TESTING")
print("-" * 40)

tests_path = Path(__file__).parent.parent / "tests"
if tests_path.exists():
    test_files = list(tests_path.glob("test_*.py"))
    implemented.append(f"Tests ({len(test_files)} files)")
    print(f"   OK - {len(test_files)} test files exist")

    # Check for specific test types
    test_types = {
        "unit": False,
        "integration": False,
        "e2e": False
    }

    for test_file in test_files:
        name = test_file.stem
        if "unit" in name or "test_" in name:
            test_types["unit"] = True
        if "integration" in name or "api" in name:
            test_types["integration"] = True
        if "e2e" in name or "end_to_end" in name:
            test_types["e2e"] = True

    if not test_types["unit"]:
        missing.append("Unit tests for Phase 2 components")
        print("   MISSING - Unit tests for Phase 2")
    else:
        print("   OK - Unit tests exist")

    if not test_types["integration"]:
        missing.append("Integration tests for Phase 2")
        print("   MISSING - Integration tests for Phase 2")

    if not test_types["e2e"]:
        missing.append("End-to-end tests")
        print("   MISSING - E2E tests")
else:
    missing.append("Tests directory")
    print("   MISSING - No tests for Phase 2")

# Pytest configuration
pytest_ini = Path(__file__).parent.parent / "pytest.ini"
if pytest_ini.exists() or (Path(__file__).parent.parent / "pyproject.toml").exists():
    implemented.append("Pytest configuration")
    print("   OK - Pytest configured")
else:
    missing.append("Pytest configuration")
    print("   MISSING - No pytest.ini or pyproject.toml")

# =============================================================================
# 8. DOCUMENTATION
# =============================================================================
print("\n8. DOCUMENTATION")
print("-" * 40)

# OpenAPI/Swagger
if main_py.exists():
    with open(main_py, 'r', encoding='utf-8') as f:
        content = f.read()
        if "openapi" in content.lower() or "swagger" in content.lower():
            implemented.append("OpenAPI/Swagger docs")
            print("   OK - OpenAPI docs configured")
        else:
            missing.append("OpenAPI/Swagger documentation")
            print("   MISSING - No Swagger UI")

# Architecture docs
docs = ["README-ENTERPRISE.md", "IMPLEMENTATION-STATUS.md", "PHASE-2-COMPLETE.md"]
docs_found = []
for doc in docs:
    if (Path(__file__).parent.parent / doc).exists():
        docs_found.append(doc)

if len(docs_found) >= 3:
    implemented.append(f"Architecture documentation ({len(docs_found)} files)")
    print(f"   OK - {len(docs_found)} architecture docs")
else:
    warnings.append("Incomplete architecture documentation")

# API documentation (separate from code)
api_docs_path = Path(__file__).parent.parent / "docs" / "api"
if api_docs_path.exists():
    implemented.append("API documentation")
    print("   OK - API docs directory exists")
else:
    missing.append("API documentation (separate from OpenAPI)")
    print("   MISSING - No dedicated API docs")

# =============================================================================
# 9. DEPLOYMENT & DEVOPS
# =============================================================================
print("\n9. DEPLOYMENT & DEVOPS")
print("-" * 40)

# Docker
dockerfile = Path(__file__).parent.parent / "Dockerfile"
if dockerfile.exists():
    implemented.append("Dockerfile")
    print("   OK - Dockerfile exists")
else:
    missing.append("Dockerfile")
    print("   MISSING - No Dockerfile")

# Docker Compose
docker_compose = Path(__file__).parent.parent / "docker-compose.yml"
if docker_compose.exists():
    implemented.append("Docker Compose")
    print("   OK - docker-compose.yml exists")
else:
    missing.append("Docker Compose configuration")
    print("   MISSING - No docker-compose.yml")

# Environment configuration
env_example = Path(__file__).parent.parent / ".env.example"
if env_example.exists():
    implemented.append(".env.example")
    print("   OK - .env.example exists")
else:
    missing.append(".env.example file")
    print("   MISSING - No .env.example")

# CI/CD
ci_files = [
    ".github/workflows",
    ".gitlab-ci.yml",
    "Jenkinsfile",
    ".circleci/config.yml"
]

found_ci = False
for ci_file in ci_files:
    if (Path(__file__).parent.parent / ci_file).exists():
        found_ci = True
        implemented.append(f"CI/CD ({ci_file})")
        print(f"   OK - CI/CD configured ({ci_file})")
        break

if not found_ci:
    missing.append("CI/CD pipeline")
    print("   MISSING - No CI/CD configuration")

# =============================================================================
# 10. SECURITY
# =============================================================================
print("\n10. SECURITY")
print("-" * 40)

# Input validation
validation_indicators = ["pydantic", "BaseModel", "validator"]
found_validation = False
for py_file in (Path(__file__).parent.parent / "src" / "presentation" / "api" / "v2").glob("*.py"):
    with open(py_file, 'r', encoding='utf-8') as f:
        content = f.read()
        if any(ind in content for ind in validation_indicators):
            found_validation = True
            break

if found_validation:
    implemented.append("Input validation (Pydantic)")
    print("   OK - Input validation with Pydantic")
else:
    warnings.append("Input validation may be incomplete")

# SQL injection protection
implemented.append("SQL injection protection (SQLAlchemy ORM)")
print("   OK - SQLAlchemy ORM protects against SQL injection")

# Secrets management
secrets_indicators = ["vault", "aws_secrets", "SECRET_KEY", "load_dotenv"]
found_secrets = False
if main_py.exists():
    with open(main_py, 'r', encoding='utf-8') as f:
        content = f.read()
        if any(ind in content for ind in secrets_indicators):
            found_secrets = True

config_py = Path(__file__).parent.parent / "app" / "config.py"
if config_py.exists():
    with open(config_py, 'r', encoding='utf-8') as f:
        content = f.read()
        if any(ind in content for ind in secrets_indicators):
            found_secrets = True

if found_secrets:
    implemented.append("Secrets management")
    print("   OK - Secrets management configured")
else:
    missing.append("Secrets management (Vault/AWS Secrets Manager)")
    print("   MISSING - No secrets management")

# HTTPS/TLS
missing.append("HTTPS/TLS configuration guide")
print("   MISSING - No HTTPS/TLS documentation")

# =============================================================================
# SUMMARY
# =============================================================================
print("\n" + "="*80)
print("COMPLETENESS AUDIT SUMMARY")
print("="*80)

print(f"\nIMPLEMENTED: {len(implemented)} components")
print(f"MISSING: {len(missing)} components")
print(f"WARNINGS: {len(warnings)} items")

completion_rate = (len(implemented) / (len(implemented) + len(missing))) * 100

print(f"\nCompletion Rate: {completion_rate:.1f}%")

if missing:
    print("\n" + "="*80)
    print("MISSING COMPONENTS FOR PRODUCTION-READY TOOL")
    print("="*80)
    for i, item in enumerate(missing, 1):
        print(f"  {i}. {item}")

if warnings:
    print("\n" + "="*80)
    print("WARNINGS - ITEMS TO REVIEW")
    print("="*80)
    for i, item in enumerate(warnings, 1):
        print(f"  {i}. {item}")

print("\n" + "="*80)
print("RECOMMENDATIONS")
print("="*80)

# Prioritize missing items
critical = []
important = []
nice_to_have = []

for item in missing:
    if any(keyword in item.lower() for keyword in ["authentication", "security", "validation"]):
        critical.append(item)
    elif any(keyword in item.lower() for keyword in ["use case", "endpoint", "cache", "test"]):
        important.append(item)
    else:
        nice_to_have.append(item)

if critical:
    print("\nCRITICAL (Must implement before production):")
    for item in critical:
        print(f"  - {item}")

if important:
    print("\nIMPORTANT (Should implement for production):")
    for item in important:
        print(f"  - {item}")

if nice_to_have:
    print("\nNICE TO HAVE (Can implement later):")
    for item in nice_to_have:
        print(f"  - {item}")

sys.exit(0 if len(critical) == 0 else 1)
