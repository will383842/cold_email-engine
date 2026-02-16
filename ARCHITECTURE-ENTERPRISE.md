# 🏗️ EMAIL ENGINE - ARCHITECTURE ENTERPRISE-GRADE

**Version** : 2.0 - Enterprise Edition
**Date** : 16 février 2026
**Statut** : 🎯 **ARCHITECTURE SCALABLE INFINIE**

---

## 📋 TABLE DES MATIÈRES

1. [Principes Architecturaux](#1-principes-architecturaux)
2. [Architecture Hexagonale (Clean Architecture)](#2-architecture-hexagonale)
3. [Structure Projet Complète](#3-structure-projet-complète)
4. [Domain-Driven Design (DDD)](#4-domain-driven-design)
5. [Patterns & Best Practices](#5-patterns--best-practices)
6. [Scalabilité & Performance](#6-scalabilité--performance)
7. [Observabilité & Monitoring](#7-observabilité--monitoring)
8. [Sécurité Enterprise](#8-sécurité-enterprise)
9. [CI/CD & DevOps](#9-cicd--devops)
10. [Testing Strategy](#10-testing-strategy)
11. [Documentation](#11-documentation)
12. [Migration Plan](#12-migration-plan)

---

## 1. PRINCIPES ARCHITECTURAUX

### 1.1 SOLID Principles

✅ **S** - Single Responsibility Principle
✅ **O** - Open/Closed Principle
✅ **L** - Liskov Substitution Principle
✅ **I** - Interface Segregation Principle
✅ **D** - Dependency Inversion Principle

### 1.2 Architecture Principles

```
┌─────────────────────────────────────────────────────────────────┐
│                    CORE PRINCIPLES                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. SEPARATION OF CONCERNS                                     │
│     - Domain ≠ Infrastructure ≠ Application ≠ Presentation     │
│                                                                 │
│  2. DEPENDENCY INVERSION                                       │
│     - Business Logic ne dépend PAS de l'infra                  │
│     - Abstractions (interfaces) partout                        │
│                                                                 │
│  3. TESTABILITY                                                │
│     - Unit tests sans base de données                          │
│     - Mocking facile (interfaces)                              │
│                                                                 │
│  4. SCALABILITY                                                │
│     - Horizontal scaling (stateless)                           │
│     - Async/Event-driven                                       │
│     - Microservices-ready                                      │
│                                                                 │
│  5. OBSERVABILITY                                              │
│     - Logging structuré (JSON)                                 │
│     - Distributed tracing                                      │
│     - Metrics (Prometheus)                                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. ARCHITECTURE HEXAGONALE

### 2.1 Layers Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     PRESENTATION LAYER                          │
│              (API REST, GraphQL, CLI, WebSockets)               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────────────────────────────────────────────┐     │
│  │            APPLICATION LAYER (Use Cases)              │     │
│  │  - CreateCampaignUseCase                             │     │
│  │  - IngestContactsUseCase                             │     │
│  │  - SelectTemplateUseCase                             │     │
│  │  - SendCampaignUseCase                               │     │
│  └───────────────────────────────────────────────────────┘     │
│                            ↓ ↑                                  │
│  ┌───────────────────────────────────────────────────────┐     │
│  │               DOMAIN LAYER (Business Logic)           │     │
│  │                                                       │     │
│  │  Entities:                                            │     │
│  │  - Contact, Campaign, EmailTemplate, Tag, etc.       │     │
│  │                                                       │     │
│  │  Value Objects:                                       │     │
│  │  - Email, PhoneNumber, Language, CountryCode         │     │
│  │                                                       │     │
│  │  Domain Services:                                     │     │
│  │  - ContactValidator, TemplateSelector, TagMatcher    │     │
│  │                                                       │     │
│  │  Domain Events:                                       │     │
│  │  - ContactIngested, CampaignLaunched, EmailSent      │     │
│  │                                                       │     │
│  │  Repository Interfaces (Ports):                       │     │
│  │  - IContactRepository, ICampaignRepository           │     │
│  └───────────────────────────────────────────────────────┘     │
│                            ↓ ↑                                  │
│  ┌───────────────────────────────────────────────────────┐     │
│  │          INFRASTRUCTURE LAYER (Adapters)              │     │
│  │                                                       │     │
│  │  Database (PostgreSQL):                               │     │
│  │  - SQLAlchemy Models                                  │     │
│  │  - Repository Implementations                         │     │
│  │                                                       │     │
│  │  External Services:                                   │     │
│  │  - MailWizz Client                                    │     │
│  │  - PowerMTA Client                                    │     │
│  │  - SMTP Validator                                     │     │
│  │  - Redis Cache                                        │     │
│  │  - Message Queue (RabbitMQ/Redis)                     │     │
│  │                                                       │     │
│  │  Event Publishers:                                    │     │
│  │  - EventBus, MessageQueue                            │     │
│  └───────────────────────────────────────────────────────┘     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Dependency Flow

```
Presentation → Application → Domain ← Infrastructure
     ↓              ↓           ↑            ↑
  FastAPI      Use Cases    Entities    Repositories
   Routes                   Services    External APIs
```

**Règle d'or** : Le Domain ne dépend de RIEN. Tout dépend du Domain.

---

## 3. STRUCTURE PROJET COMPLÈTE

### 3.1 Organisation Dossiers

```
email-engine/
│
├── src/                                    # Code source principal
│   ├── domain/                             # 🎯 DOMAIN LAYER (Business Logic)
│   │   ├── __init__.py
│   │   │
│   │   ├── entities/                       # Entités métier
│   │   │   ├── __init__.py
│   │   │   ├── base.py                     # BaseEntity (ID, timestamps)
│   │   │   ├── contact.py                  # Contact entity
│   │   │   ├── campaign.py                 # Campaign entity
│   │   │   ├── email_template.py           # EmailTemplate entity
│   │   │   ├── tag.py                      # Tag entity
│   │   │   ├── data_source.py              # DataSource entity
│   │   │   ├── mailwizz_instance.py        # MailWizzInstance entity
│   │   │   └── tenant.py                   # Tenant entity (multi-tenant)
│   │   │
│   │   ├── value_objects/                  # Value Objects (immutables)
│   │   │   ├── __init__.py
│   │   │   ├── email.py                    # Email VO (validation)
│   │   │   ├── phone_number.py             # PhoneNumber VO
│   │   │   ├── language.py                 # Language VO (9 langues)
│   │   │   ├── country_code.py             # CountryCode VO (ISO)
│   │   │   ├── tag_slug.py                 # TagSlug VO (normalized)
│   │   │   └── tenant_id.py                # TenantId VO
│   │   │
│   │   ├── services/                       # Domain Services (business logic)
│   │   │   ├── __init__.py
│   │   │   ├── contact_validator.py        # Validation métier contacts
│   │   │   ├── template_selector.py        # Sélection template (catégorie+langue+tags)
│   │   │   ├── tag_matcher.py              # Matching tags (ALL, ANY, EXCLUDE)
│   │   │   ├── campaign_segmenter.py       # Segmentation campagnes
│   │   │   ├── auto_tagger.py              # Auto-attribution tags
│   │   │   └── deduplicator.py             # Déduplication contacts
│   │   │
│   │   ├── events/                         # Domain Events
│   │   │   ├── __init__.py
│   │   │   ├── base.py                     # BaseDomainEvent
│   │   │   ├── contact_events.py           # ContactIngested, ContactValidated, etc.
│   │   │   ├── campaign_events.py          # CampaignCreated, CampaignLaunched, etc.
│   │   │   └── email_events.py             # EmailSent, EmailOpened, EmailBounced, etc.
│   │   │
│   │   ├── repositories/                   # Repository Interfaces (Ports)
│   │   │   ├── __init__.py
│   │   │   ├── base.py                     # IBaseRepository (CRUD générique)
│   │   │   ├── contact_repository.py       # IContactRepository
│   │   │   ├── campaign_repository.py      # ICampaignRepository
│   │   │   ├── email_template_repository.py
│   │   │   ├── tag_repository.py
│   │   │   ├── data_source_repository.py
│   │   │   └── tenant_repository.py
│   │   │
│   │   ├── exceptions/                     # Domain Exceptions
│   │   │   ├── __init__.py
│   │   │   ├── base.py                     # BaseDomainException
│   │   │   ├── validation_errors.py        # InvalidEmailError, etc.
│   │   │   ├── business_errors.py          # DuplicateContactError, etc.
│   │   │   └── not_found_errors.py         # ContactNotFoundError, etc.
│   │   │
│   │   └── specifications/                 # Specification Pattern (filtres complexes)
│   │       ├── __init__.py
│   │       ├── base.py                     # BaseSpecification
│   │       ├── contact_specs.py            # ActiveContacts, ValidatedContacts, etc.
│   │       └── campaign_specs.py           # ScheduledCampaigns, etc.
│   │
│   ├── application/                        # 🎯 APPLICATION LAYER (Use Cases)
│   │   ├── __init__.py
│   │   │
│   │   ├── use_cases/                      # Use Cases (orchestration)
│   │   │   ├── __init__.py
│   │   │   │
│   │   │   ├── contacts/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── ingest_contacts.py      # IngestContactsUseCase
│   │   │   │   ├── validate_contact.py     # ValidateContactUseCase
│   │   │   │   ├── enrich_contact.py       # EnrichContactUseCase
│   │   │   │   ├── inject_contact.py       # InjectContactToMailwizzUseCase
│   │   │   │   ├── tag_contact.py          # TagContactUseCase
│   │   │   │   └── get_contact.py          # GetContactUseCase
│   │   │   │
│   │   │   ├── campaigns/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── create_campaign.py      # CreateCampaignUseCase
│   │   │   │   ├── launch_campaign.py      # LaunchCampaignUseCase
│   │   │   │   ├── pause_campaign.py       # PauseCampaignUseCase
│   │   │   │   ├── select_contacts.py      # SelectContactsForCampaignUseCase
│   │   │   │   └── get_campaign_stats.py   # GetCampaignStatsUseCase
│   │   │   │
│   │   │   ├── templates/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── create_template.py      # CreateTemplateUseCase
│   │   │   │   ├── select_template.py      # SelectTemplateUseCase
│   │   │   │   └── render_template.py      # RenderTemplateUseCase
│   │   │   │
│   │   │   └── data_sources/
│   │   │       ├── __init__.py
│   │   │       ├── register_source.py      # RegisterDataSourceUseCase
│   │   │       └── sync_source.py          # SyncDataSourceUseCase
│   │   │
│   │   ├── dto/                            # Data Transfer Objects
│   │   │   ├── __init__.py
│   │   │   ├── contact_dto.py              # ContactCreateDTO, ContactResponseDTO
│   │   │   ├── campaign_dto.py             # CampaignCreateDTO, etc.
│   │   │   ├── template_dto.py
│   │   │   └── data_source_dto.py
│   │   │
│   │   ├── mappers/                        # DTO ↔ Entity Mappers
│   │   │   ├── __init__.py
│   │   │   ├── contact_mapper.py           # ContactMapper
│   │   │   ├── campaign_mapper.py
│   │   │   └── template_mapper.py
│   │   │
│   │   └── interfaces/                     # Application Interfaces
│   │       ├── __init__.py
│   │       ├── unit_of_work.py             # IUnitOfWork (transactions)
│   │       ├── event_bus.py                # IEventBus (pub/sub)
│   │       ├── cache.py                    # ICache
│   │       └── message_queue.py            # IMessageQueue
│   │
│   ├── infrastructure/                     # 🎯 INFRASTRUCTURE LAYER (Adapters)
│   │   ├── __init__.py
│   │   │
│   │   ├── persistence/                    # Database (PostgreSQL)
│   │   │   ├── __init__.py
│   │   │   ├── database.py                 # SQLAlchemy engine, sessions
│   │   │   ├── unit_of_work.py             # UnitOfWork implementation
│   │   │   │
│   │   │   ├── models/                     # SQLAlchemy Models (ORM)
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py                 # BaseModel
│   │   │   │   ├── contact_model.py        # ContactModel
│   │   │   │   ├── campaign_model.py       # CampaignModel
│   │   │   │   ├── email_template_model.py
│   │   │   │   ├── tag_model.py
│   │   │   │   ├── data_source_model.py
│   │   │   │   ├── tenant_model.py
│   │   │   │   └── contact_event_model.py
│   │   │   │
│   │   │   ├── repositories/               # Repository Implementations
│   │   │   │   ├── __init__.py
│   │   │   │   ├── contact_repository.py   # ContactRepository (impl)
│   │   │   │   ├── campaign_repository.py
│   │   │   │   ├── email_template_repository.py
│   │   │   │   ├── tag_repository.py
│   │   │   │   └── data_source_repository.py
│   │   │   │
│   │   │   └── migrations/                 # Alembic migrations
│   │   │       ├── env.py
│   │   │       ├── script.py.mako
│   │   │       └── versions/
│   │   │           └── 2026_02_16_enterprise_schema.py
│   │   │
│   │   ├── cache/                          # Redis Cache
│   │   │   ├── __init__.py
│   │   │   ├── redis_client.py             # Redis connection
│   │   │   ├── cache_service.py            # Cache implementation
│   │   │   └── cache_keys.py               # Cache key patterns
│   │   │
│   │   ├── messaging/                      # Message Queue (RabbitMQ/Redis)
│   │   │   ├── __init__.py
│   │   │   ├── event_bus.py                # EventBus implementation
│   │   │   ├── message_queue.py            # MessageQueue implementation
│   │   │   └── consumers/                  # Message consumers
│   │   │       ├── __init__.py
│   │   │       ├── contact_consumer.py
│   │   │       └── campaign_consumer.py
│   │   │
│   │   ├── external/                       # External Services (Adapters)
│   │   │   ├── __init__.py
│   │   │   │
│   │   │   ├── mailwizz/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── client.py               # MailWizz API client
│   │   │   │   ├── multi_client.py         # Multi-instance client
│   │   │   │   ├── mysql_client.py         # MySQL fallback
│   │   │   │   └── exceptions.py
│   │   │   │
│   │   │   ├── powermta/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── client.py               # PowerMTA API
│   │   │   │   └── config_parser.py        # PowerMTA config reader
│   │   │   │
│   │   │   ├── smtp/
│   │   │   │   ├── __init__.py
│   │   │   │   └── validator.py            # SMTP validation
│   │   │   │
│   │   │   ├── telegram/
│   │   │   │   ├── __init__.py
│   │   │   │   └── alerts.py               # Telegram alerts
│   │   │   │
│   │   │   └── scraper_pro/
│   │   │       ├── __init__.py
│   │   │       └── webhook_client.py       # Scraper-Pro webhook sender
│   │   │
│   │   ├── background/                     # Background Jobs (Celery/RQ)
│   │   │   ├── __init__.py
│   │   │   ├── celery_app.py               # Celery config
│   │   │   │
│   │   │   ├── tasks/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── contact_tasks.py        # Validation, enrichment batch
│   │   │   │   ├── campaign_tasks.py       # Launch, stats aggregation
│   │   │   │   ├── mailwizz_tasks.py       # Injection batch
│   │   │   │   └── monitoring_tasks.py     # Health checks, metrics
│   │   │   │
│   │   │   └── schedulers/
│   │   │       ├── __init__.py
│   │   │       └── cron_jobs.py            # APScheduler cron jobs
│   │   │
│   │   ├── observability/                  # Logging, Tracing, Metrics
│   │   │   ├── __init__.py
│   │   │   ├── logging.py                  # Structured logging config
│   │   │   ├── tracing.py                  # OpenTelemetry setup
│   │   │   ├── metrics.py                  # Prometheus metrics
│   │   │   └── sentry.py                   # Sentry error tracking
│   │   │
│   │   └── security/                       # Security
│   │       ├── __init__.py
│   │       ├── encryption.py               # Fernet encryption
│   │       ├── hashing.py                  # Password hashing (bcrypt)
│   │       ├── jwt.py                      # JWT tokens
│   │       └── rate_limiter.py             # Redis-based rate limiting
│   │
│   ├── presentation/                       # 🎯 PRESENTATION LAYER (API)
│   │   ├── __init__.py
│   │   │
│   │   ├── api/                            # REST API (FastAPI)
│   │   │   ├── __init__.py
│   │   │   ├── main.py                     # FastAPI app
│   │   │   ├── dependencies.py             # DI container
│   │   │   ├── middleware.py               # CORS, Auth, Logging
│   │   │   │
│   │   │   ├── v1/                         # API v1
│   │   │   │   ├── __init__.py
│   │   │   │   ├── router.py               # Main router v1
│   │   │   │   │
│   │   │   │   ├── endpoints/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── auth.py             # Auth endpoints
│   │   │   │   │   ├── contacts.py         # Contacts CRUD + ingest
│   │   │   │   │   ├── campaigns.py        # Campaigns CRUD + launch
│   │   │   │   │   ├── email_templates.py  # Templates CRUD
│   │   │   │   │   ├── tags.py             # Tags CRUD
│   │   │   │   │   ├── data_sources.py     # Data sources CRUD
│   │   │   │   │   ├── mailwizz.py         # MailWizz instances config
│   │   │   │   │   ├── webhooks.py         # Webhooks (MailWizz, PMTA)
│   │   │   │   │   ├── health.py           # Health checks
│   │   │   │   │   └── metrics.py          # Prometheus metrics endpoint
│   │   │   │   │
│   │   │   │   └── schemas/                # Pydantic schemas (API contracts)
│   │   │   │       ├── __init__.py
│   │   │   │       ├── contact_schemas.py
│   │   │   │       ├── campaign_schemas.py
│   │   │   │       ├── template_schemas.py
│   │   │   │       └── common_schemas.py   # ErrorResponse, etc.
│   │   │   │
│   │   │   └── v2/                         # API v2 (future)
│   │   │       └── __init__.py
│   │   │
│   │   └── cli/                            # CLI (Typer)
│   │       ├── __init__.py
│   │       ├── main.py                     # Typer app
│   │       └── commands/
│   │           ├── __init__.py
│   │           ├── contacts.py             # CLI contacts commands
│   │           ├── campaigns.py            # CLI campaigns commands
│   │           └── admin.py                # Admin commands
│   │
│   └── shared/                             # 🎯 SHARED (Code commun)
│       ├── __init__.py
│       ├── config.py                       # Configuration (Pydantic Settings)
│       ├── constants.py                    # Constantes globales
│       ├── enums.py                        # Enums globaux
│       └── utils/
│           ├── __init__.py
│           ├── date_utils.py
│           ├── string_utils.py
│           └── validation_utils.py
│
├── tests/                                  # 🧪 TESTS
│   ├── __init__.py
│   │
│   ├── unit/                               # Tests unitaires
│   │   ├── __init__.py
│   │   ├── domain/
│   │   │   ├── entities/
│   │   │   ├── value_objects/
│   │   │   └── services/
│   │   └── application/
│   │       └── use_cases/
│   │
│   ├── integration/                        # Tests intégration
│   │   ├── __init__.py
│   │   ├── repositories/
│   │   ├── external_services/
│   │   └── api/
│   │
│   ├── e2e/                                # Tests end-to-end
│   │   ├── __init__.py
│   │   └── scenarios/
│   │
│   ├── performance/                        # Tests performance
│   │   ├── __init__.py
│   │   └── load_tests.py
│   │
│   └── fixtures/                           # Fixtures (données test)
│       ├── __init__.py
│       ├── contacts.py
│       └── campaigns.py
│
├── scripts/                                # 📜 SCRIPTS
│   ├── seed_data.py                        # Seed database (tags, tenants, etc.)
│   ├── import_templates.py                 # Import HTML templates
│   ├── migrate_data.py                     # Data migrations
│   └── performance_benchmark.py            # Benchmarking
│
├── docs/                                   # 📚 DOCUMENTATION
│   ├── architecture/
│   │   ├── adr/                            # Architecture Decision Records
│   │   │   ├── 001-hexagonal-architecture.md
│   │   │   ├── 002-multi-tenant.md
│   │   │   └── 003-event-driven.md
│   │   ├── diagrams/
│   │   │   ├── system-architecture.png
│   │   │   ├── data-flow.png
│   │   │   └── deployment.png
│   │   └── domain-model.md
│   │
│   ├── api/
│   │   ├── openapi.yaml                    # OpenAPI spec
│   │   └── postman_collection.json
│   │
│   ├── runbooks/
│   │   ├── deployment.md
│   │   ├── rollback.md
│   │   └── troubleshooting.md
│   │
│   └── onboarding/
│       ├── developer-setup.md
│       └── architecture-overview.md
│
├── deployments/                            # 🚀 DEPLOYMENT
│   ├── docker/
│   │   ├── Dockerfile                      # Multi-stage Dockerfile
│   │   ├── docker-compose.yml              # Local development
│   │   └── docker-compose.prod.yml         # Production
│   │
│   ├── kubernetes/                         # K8s manifests
│   │   ├── namespace.yaml
│   │   ├── configmap.yaml
│   │   ├── secrets.yaml
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   ├── ingress.yaml
│   │   └── hpa.yaml                        # Horizontal Pod Autoscaler
│   │
│   └── terraform/                          # Infrastructure as Code
│       ├── main.tf
│       ├── variables.tf
│       └── outputs.tf
│
├── monitoring/                             # 📊 MONITORING
│   ├── prometheus/
│   │   └── prometheus.yml
│   ├── grafana/
│   │   └── dashboards/
│   │       ├── application.json
│   │       ├── infrastructure.json
│   │       └── business.json
│   └── alertmanager/
│       └── config.yml
│
├── .github/                                # 🔄 CI/CD
│   └── workflows/
│       ├── ci.yml                          # Continuous Integration
│       ├── cd.yml                          # Continuous Deployment
│       ├── security.yml                    # Security scanning
│       └── performance.yml                 # Performance tests
│
├── .pre-commit-config.yaml                 # Pre-commit hooks
├── pyproject.toml                          # Poetry config
├── poetry.lock
├── requirements.txt                        # Pip requirements (CI/CD)
├── .env.example                            # Environment variables template
├── .gitignore
├── README.md
├── CHANGELOG.md
├── LICENSE
└── CONTRIBUTING.md
```

---

## 4. DOMAIN-DRIVEN DESIGN (DDD)

### 4.1 Bounded Contexts

```
┌─────────────────────────────────────────────────────────────────┐
│                      EMAIL ENGINE SYSTEM                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌────────────────────┐  ┌────────────────────┐               │
│  │  CONTACT CONTEXT   │  │  CAMPAIGN CONTEXT  │               │
│  │                    │  │                    │               │
│  │  - Contact         │  │  - Campaign        │               │
│  │  - Tag             │  │  - EmailTemplate   │               │
│  │  - DataSource      │  │  - CampaignStats   │               │
│  │  - Validation      │  │  - Segmentation    │               │
│  └────────────────────┘  └────────────────────┘               │
│           ↓ ↑                      ↓ ↑                         │
│  ┌────────────────────┐  ┌────────────────────┐               │
│  │  DELIVERY CONTEXT  │  │  TENANT CONTEXT    │               │
│  │                    │  │                    │               │
│  │  - MailWizz        │  │  - Tenant          │               │
│  │  - PowerMTA        │  │  - Configuration   │               │
│  │  - EmailSending    │  │  - Multi-tenancy   │               │
│  │  - Tracking        │  │  - Isolation       │               │
│  └────────────────────┘  └────────────────────┘               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Aggregates

#### Contact Aggregate

```python
# src/domain/entities/contact.py

from typing import List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from src.domain.entities.base import BaseEntity
from src.domain.value_objects.email import Email
from src.domain.value_objects.language import Language
from src.domain.value_objects.country_code import CountryCode
from src.domain.value_objects.tag_slug import TagSlug
from src.domain.events.contact_events import ContactIngested, ContactValidated


@dataclass
class Contact(BaseEntity):
    """
    Contact Aggregate Root.

    Invariants:
    - Email must be valid and unique
    - Language must be supported or fallback to 'en'
    - Tags must be normalized
    - Category must exist in tenant config
    """

    # Identity
    email: Email
    tenant_id: str

    # Personal info
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None

    # Location & Language
    country_code: Optional[CountryCode] = None
    language: Language = Language('en')

    # Classification
    category: str
    subcategory: Optional[str] = None
    tags: List[TagSlug] = field(default_factory=list)
    score: int = 50

    # Source tracking
    source_id: str
    import_batch_id: Optional[str] = None
    raw_data: dict = field(default_factory=dict)

    # Validation
    email_valid: Optional[bool] = None
    email_validation_result: Optional[dict] = None

    # MailWizz sync
    mailwizz_instance: Optional[str] = None
    mailwizz_list_id: Optional[int] = None
    mailwizz_subscriber_uid: Optional[str] = None
    injected_at: Optional[datetime] = None

    # Status
    status: str = 'pending'
    status_changed_at: Optional[datetime] = None

    def __post_init__(self):
        """Validate invariants."""
        super().__post_init__()
        self._validate_invariants()

    def _validate_invariants(self):
        """Business rules validation."""
        if not self.email.is_valid():
            raise InvalidEmailError(f"Invalid email: {self.email.value}")

        if self.score < 0 or self.score > 100:
            raise ValueError("Score must be between 0 and 100")

    # 🎯 BUSINESS METHODS

    def validate_email(self, is_valid: bool, validation_result: dict):
        """Mark email as validated."""
        self.email_valid = is_valid
        self.email_validation_result = validation_result
        self.status = 'validated' if is_valid else 'invalid'
        self.status_changed_at = datetime.utcnow()

        # Raise domain event
        if is_valid:
            self.add_domain_event(ContactValidated(
                contact_id=self.id,
                email=self.email.value,
                tenant_id=self.tenant_id
            ))

    def add_tags(self, tags: List[str]):
        """Add tags to contact (normalized)."""
        for tag in tags:
            tag_slug = TagSlug(tag)
            if tag_slug not in self.tags:
                self.tags.append(tag_slug)

    def remove_tags(self, tags: List[str]):
        """Remove tags from contact."""
        tags_to_remove = [TagSlug(t) for t in tags]
        self.tags = [t for t in self.tags if t not in tags_to_remove]

    def inject_to_mailwizz(
        self,
        instance_id: str,
        list_id: int,
        subscriber_uid: str
    ):
        """Mark as injected to MailWizz."""
        self.mailwizz_instance = instance_id
        self.mailwizz_list_id = list_id
        self.mailwizz_subscriber_uid = subscriber_uid
        self.injected_at = datetime.utcnow()
        self.status = 'injected'
        self.status_changed_at = datetime.utcnow()

    def can_be_contacted(self) -> bool:
        """Check if contact can receive emails."""
        return (
            self.email_valid == True
            and self.status not in ['bounced', 'unsubscribed', 'blacklisted']
            and 'unsubscribed' not in [t.value for t in self.tags]
        )
```

#### Campaign Aggregate

```python
# src/domain/entities/campaign.py

from typing import List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from src.domain.entities.base import BaseEntity
from src.domain.value_objects.tag_slug import TagSlug
from src.domain.events.campaign_events import CampaignCreated, CampaignLaunched


@dataclass
class Campaign(BaseEntity):
    """
    Campaign Aggregate Root.

    Invariants:
    - Must have template
    - Must have target criteria (category OR tags)
    - MailWizz instance must exist
    - Scheduled date must be future
    """

    # Identity
    tenant_id: str
    name: str
    description: Optional[str] = None

    # Source (optional)
    source_id: Optional[str] = None

    # Target MailWizz
    mailwizz_instance: str
    mailwizz_campaign_id: Optional[int] = None
    mailwizz_list_id: int

    # Template
    email_template_id: int
    subject_line: str
    from_name: str
    from_email: str

    # Segmentation (tags-based)
    target_category: Optional[str] = None
    target_tags_all: List[TagSlug] = field(default_factory=list)   # AND
    target_tags_any: List[TagSlug] = field(default_factory=list)   # OR
    exclude_tags: List[TagSlug] = field(default_factory=list)
    target_country_codes: List[str] = field(default_factory=list)
    max_contacts: Optional[int] = None

    # Scheduling
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Status
    status: str = 'draft'

    # Stats (denormalized)
    total_sent: int = 0
    total_delivered: int = 0
    total_bounced: int = 0
    total_opened: int = 0
    total_clicked: int = 0
    total_unsubscribed: int = 0

    def __post_init__(self):
        """Validate invariants."""
        super().__post_init__()
        self._validate_invariants()

    def _validate_invariants(self):
        """Business rules validation."""
        # Must have segmentation criteria
        if not self.target_category and not self.target_tags_all and not self.target_tags_any:
            raise ValueError("Campaign must have target criteria (category or tags)")

        # Scheduled date must be future
        if self.scheduled_at and self.scheduled_at < datetime.utcnow():
            raise ValueError("Scheduled date must be in the future")

    # 🎯 BUSINESS METHODS

    def schedule(self, scheduled_at: datetime):
        """Schedule campaign."""
        if scheduled_at < datetime.utcnow():
            raise ValueError("Cannot schedule in the past")

        self.scheduled_at = scheduled_at
        self.status = 'scheduled'

    def launch(self, mailwizz_campaign_id: int):
        """Launch campaign."""
        if self.status not in ['scheduled', 'draft']:
            raise ValueError(f"Cannot launch campaign in status {self.status}")

        self.mailwizz_campaign_id = mailwizz_campaign_id
        self.started_at = datetime.utcnow()
        self.status = 'running'

        # Raise domain event
        self.add_domain_event(CampaignLaunched(
            campaign_id=self.id,
            tenant_id=self.tenant_id,
            name=self.name
        ))

    def pause(self):
        """Pause running campaign."""
        if self.status != 'running':
            raise ValueError("Can only pause running campaigns")

        self.status = 'paused'

    def resume(self):
        """Resume paused campaign."""
        if self.status != 'paused':
            raise ValueError("Can only resume paused campaigns")

        self.status = 'running'

    def complete(self):
        """Mark campaign as completed."""
        self.completed_at = datetime.utcnow()
        self.status = 'completed'

    def update_stats(
        self,
        sent: int = 0,
        delivered: int = 0,
        bounced: int = 0,
        opened: int = 0,
        clicked: int = 0,
        unsubscribed: int = 0
    ):
        """Update campaign stats."""
        self.total_sent += sent
        self.total_delivered += delivered
        self.total_bounced += bounced
        self.total_opened += opened
        self.total_clicked += clicked
        self.total_unsubscribed += unsubscribed
```

### 4.3 Value Objects

```python
# src/domain/value_objects/email.py

from dataclasses import dataclass
import re
from typing import Optional


@dataclass(frozen=True)
class Email:
    """
    Email Value Object.

    Immutable, validated email address.
    """
    value: str

    EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

    def __post_init__(self):
        """Validate email format."""
        if not self.is_valid():
            raise ValueError(f"Invalid email format: {self.value}")

    def is_valid(self) -> bool:
        """Check if email is valid."""
        return bool(self.EMAIL_REGEX.match(self.value))

    @property
    def domain(self) -> str:
        """Extract domain from email."""
        return self.value.split('@')[1] if '@' in self.value else ''

    @property
    def local_part(self) -> str:
        """Extract local part from email."""
        return self.value.split('@')[0] if '@' in self.value else ''

    def __str__(self) -> str:
        return self.value

    def __hash__(self) -> int:
        return hash(self.value.lower())

    def __eq__(self, other) -> bool:
        if not isinstance(other, Email):
            return False
        return self.value.lower() == other.value.lower()
```

```python
# src/domain/value_objects/language.py

from dataclasses import dataclass
from typing import ClassVar, List


@dataclass(frozen=True)
class Language:
    """
    Language Value Object.

    Supports 9 languages + fallback to English.
    """
    value: str

    SUPPORTED_LANGUAGES: ClassVar[List[str]] = [
        'fr', 'en', 'es', 'de', 'pt', 'ru', 'zh', 'hi', 'ar'
    ]
    FALLBACK: ClassVar[str] = 'en'

    def __post_init__(self):
        """Validate and normalize language."""
        if not self.is_supported():
            # Use object.__setattr__ because frozen=True
            object.__setattr__(self, 'value', self.FALLBACK)

    def is_supported(self) -> bool:
        """Check if language is supported."""
        return self.value.lower() in self.SUPPORTED_LANGUAGES

    def __str__(self) -> str:
        return self.value

    def __hash__(self) -> int:
        return hash(self.value.lower())

    def __eq__(self, other) -> bool:
        if not isinstance(other, Language):
            return False
        return self.value.lower() == other.value.lower()
```

```python
# src/domain/value_objects/tag_slug.py

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class TagSlug:
    """
    Tag Slug Value Object.

    Normalized tag: lowercase, underscores, no spaces.
    """
    value: str

    def __post_init__(self):
        """Normalize tag."""
        normalized = self._normalize(self.value)
        object.__setattr__(self, 'value', normalized)

    def _normalize(self, tag: str) -> str:
        """Normalize tag: lowercase, underscores, no spaces."""
        # Lowercase
        tag = tag.lower().strip()

        # Replace spaces and hyphens with underscores
        tag = re.sub(r'[\s\-]+', '_', tag)

        # Remove special characters
        tag = re.sub(r'[^a-z0-9_]', '', tag)

        # Remove duplicate underscores
        tag = re.sub(r'_+', '_', tag)

        # Remove leading/trailing underscores
        tag = tag.strip('_')

        return tag

    def __str__(self) -> str:
        return self.value

    def __hash__(self) -> int:
        return hash(self.value)
```

### 4.4 Domain Events

```python
# src/domain/events/base.py

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import uuid


@dataclass
class BaseDomainEvent:
    """Base class for all domain events."""

    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    occurred_at: datetime = field(default_factory=datetime.utcnow)
    aggregate_id: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert event to dictionary."""
        return {
            'event_id': self.event_id,
            'event_type': self.__class__.__name__,
            'occurred_at': self.occurred_at.isoformat(),
            'aggregate_id': self.aggregate_id,
            'data': self._event_data()
        }

    def _event_data(self) -> dict:
        """Override in subclasses to provide event-specific data."""
        return {}
```

```python
# src/domain/events/contact_events.py

from dataclasses import dataclass
from src.domain.events.base import BaseDomainEvent


@dataclass
class ContactIngested(BaseDomainEvent):
    """Contact was ingested from external source."""

    contact_id: str
    email: str
    tenant_id: str
    source_id: str

    def __post_init__(self):
        self.aggregate_id = self.contact_id

    def _event_data(self) -> dict:
        return {
            'contact_id': self.contact_id,
            'email': self.email,
            'tenant_id': self.tenant_id,
            'source_id': self.source_id
        }


@dataclass
class ContactValidated(BaseDomainEvent):
    """Contact email was validated."""

    contact_id: str
    email: str
    tenant_id: str
    is_valid: bool

    def __post_init__(self):
        self.aggregate_id = self.contact_id

    def _event_data(self) -> dict:
        return {
            'contact_id': self.contact_id,
            'email': self.email,
            'is_valid': self.is_valid
        }


@dataclass
class ContactInjectedToMailwizz(BaseDomainEvent):
    """Contact was injected to MailWizz."""

    contact_id: str
    email: str
    mailwizz_instance: str
    mailwizz_list_id: int
    subscriber_uid: str

    def __post_init__(self):
        self.aggregate_id = self.contact_id

    def _event_data(self) -> dict:
        return {
            'contact_id': self.contact_id,
            'email': self.email,
            'mailwizz_instance': self.mailwizz_instance,
            'mailwizz_list_id': self.mailwizz_list_id,
            'subscriber_uid': self.subscriber_uid
        }
```

---

## 5. PATTERNS & BEST PRACTICES

### 5.1 Repository Pattern

```python
# src/domain/repositories/base.py

from abc import ABC, abstractmethod
from typing import Generic, TypeVar, List, Optional

T = TypeVar('T')


class IBaseRepository(ABC, Generic[T]):
    """Base repository interface (Port)."""

    @abstractmethod
    async def get_by_id(self, id: str) -> Optional[T]:
        """Get entity by ID."""
        pass

    @abstractmethod
    async def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        """Get all entities with pagination."""
        pass

    @abstractmethod
    async def add(self, entity: T) -> T:
        """Add new entity."""
        pass

    @abstractmethod
    async def update(self, entity: T) -> T:
        """Update existing entity."""
        pass

    @abstractmethod
    async def delete(self, id: str) -> bool:
        """Delete entity by ID."""
        pass

    @abstractmethod
    async def count(self) -> int:
        """Count total entities."""
        pass
```

```python
# src/domain/repositories/contact_repository.py

from abc import abstractmethod
from typing import List, Optional
from src.domain.repositories.base import IBaseRepository
from src.domain.entities.contact import Contact
from src.domain.specifications.base import Specification


class IContactRepository(IBaseRepository[Contact]):
    """Contact repository interface (Port)."""

    @abstractmethod
    async def get_by_email(self, email: str, tenant_id: str) -> Optional[Contact]:
        """Get contact by email and tenant."""
        pass

    @abstractmethod
    async def find_by_specification(
        self,
        spec: Specification,
        skip: int = 0,
        limit: int = 100
    ) -> List[Contact]:
        """Find contacts matching specification."""
        pass

    @abstractmethod
    async def find_by_tags(
        self,
        tenant_id: str,
        tags_all: List[str] = None,
        tags_any: List[str] = None,
        exclude_tags: List[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Contact]:
        """Find contacts by tags criteria."""
        pass

    @abstractmethod
    async def batch_insert(self, contacts: List[Contact]) -> List[Contact]:
        """Batch insert contacts (optimized)."""
        pass

    @abstractmethod
    async def count_by_source(self, source_id: str, tenant_id: str) -> int:
        """Count contacts by source."""
        pass
```

```python
# src/infrastructure/persistence/repositories/contact_repository.py

from typing import List, Optional
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.repositories.contact_repository import IContactRepository
from src.domain.entities.contact import Contact
from src.domain.specifications.base import Specification
from src.infrastructure.persistence.models.contact_model import ContactModel
from src.application.mappers.contact_mapper import ContactMapper


class ContactRepository(IContactRepository):
    """Contact repository implementation (Adapter)."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.mapper = ContactMapper()

    async def get_by_id(self, id: str) -> Optional[Contact]:
        """Get contact by ID."""
        result = await self.session.execute(
            select(ContactModel).where(ContactModel.id == id)
        )
        model = result.scalar_one_or_none()

        if not model:
            return None

        return self.mapper.to_entity(model)

    async def get_by_email(self, email: str, tenant_id: str) -> Optional[Contact]:
        """Get contact by email and tenant."""
        result = await self.session.execute(
            select(ContactModel).where(
                and_(
                    ContactModel.email == email.lower(),
                    ContactModel.tenant_id == tenant_id
                )
            )
        )
        model = result.scalar_one_or_none()

        if not model:
            return None

        return self.mapper.to_entity(model)

    async def add(self, entity: Contact) -> Contact:
        """Add new contact."""
        model = self.mapper.to_model(entity)
        self.session.add(model)
        await self.session.flush()  # Get ID without commit
        await self.session.refresh(model)

        return self.mapper.to_entity(model)

    async def batch_insert(self, contacts: List[Contact]) -> List[Contact]:
        """Batch insert contacts (optimized)."""
        models = [self.mapper.to_model(c) for c in contacts]

        self.session.add_all(models)
        await self.session.flush()

        # Refresh all to get IDs
        for model in models:
            await self.session.refresh(model)

        return [self.mapper.to_entity(m) for m in models]

    async def find_by_tags(
        self,
        tenant_id: str,
        tags_all: List[str] = None,
        tags_any: List[str] = None,
        exclude_tags: List[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Contact]:
        """Find contacts by tags criteria."""
        query = select(ContactModel).where(ContactModel.tenant_id == tenant_id)

        # Tags ALL (AND logic)
        if tags_all:
            for tag in tags_all:
                query = query.where(ContactModel.tags.contains([tag]))

        # Tags ANY (OR logic)
        if tags_any:
            or_conditions = [ContactModel.tags.contains([tag]) for tag in tags_any]
            query = query.where(or_(*or_conditions))

        # Exclude tags
        if exclude_tags:
            for tag in exclude_tags:
                query = query.where(~ContactModel.tags.contains([tag]))

        # Pagination
        query = query.offset(skip).limit(limit)

        result = await self.session.execute(query)
        models = result.scalars().all()

        return [self.mapper.to_entity(m) for m in models]

    # ... autres méthodes
```

### 5.2 Unit of Work Pattern

```python
# src/application/interfaces/unit_of_work.py

from abc import ABC, abstractmethod
from typing import AsyncContextManager

from src.domain.repositories.contact_repository import IContactRepository
from src.domain.repositories.campaign_repository import ICampaignRepository
from src.domain.repositories.email_template_repository import IEmailTemplateRepository
from src.domain.repositories.tag_repository import ITagRepository


class IUnitOfWork(ABC, AsyncContextManager):
    """
    Unit of Work interface.

    Manages transactions and provides access to repositories.
    """

    contacts: IContactRepository
    campaigns: ICampaignRepository
    email_templates: IEmailTemplateRepository
    tags: ITagRepository

    @abstractmethod
    async def commit(self) -> None:
        """Commit transaction."""
        pass

    @abstractmethod
    async def rollback(self) -> None:
        """Rollback transaction."""
        pass
```

```python
# src/infrastructure/persistence/unit_of_work.py

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.application.interfaces.unit_of_work import IUnitOfWork
from src.infrastructure.persistence.repositories.contact_repository import ContactRepository
from src.infrastructure.persistence.repositories.campaign_repository import CampaignRepository
from src.infrastructure.persistence.repositories.email_template_repository import EmailTemplateRepository
from src.infrastructure.persistence.repositories.tag_repository import TagRepository


class UnitOfWork(IUnitOfWork):
    """Unit of Work implementation with SQLAlchemy."""

    def __init__(self, session_factory: async_sessionmaker):
        self.session_factory = session_factory
        self.session: AsyncSession = None

    async def __aenter__(self):
        """Start transaction."""
        self.session = self.session_factory()

        # Initialize repositories
        self.contacts = ContactRepository(self.session)
        self.campaigns = CampaignRepository(self.session)
        self.email_templates = EmailTemplateRepository(self.session)
        self.tags = TagRepository(self.session)

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """End transaction."""
        if exc_type is not None:
            await self.rollback()

        await self.session.close()

    async def commit(self) -> None:
        """Commit transaction."""
        await self.session.commit()

    async def rollback(self) -> None:
        """Rollback transaction."""
        await self.session.rollback()
```

### 5.3 Use Case Pattern

```python
# src/application/use_cases/contacts/ingest_contacts.py

from typing import List
from dataclasses import dataclass

from src.application.interfaces.unit_of_work import IUnitOfWork
from src.application.interfaces.event_bus import IEventBus
from src.application.dto.contact_dto import ContactCreateDTO, ContactResponseDTO
from src.application.mappers.contact_mapper import ContactMapper
from src.domain.entities.contact import Contact
from src.domain.services.auto_tagger import AutoTagger
from src.domain.services.deduplicator import Deduplicator
from src.domain.events.contact_events import ContactIngested


@dataclass
class IngestContactsCommand:
    """Command to ingest contacts."""

    source_id: str
    tenant_id: str
    contacts: List[ContactCreateDTO]
    auto_tag: bool = True


@dataclass
class IngestContactsResult:
    """Result of contact ingestion."""

    batch_id: str
    accepted: int
    duplicates: int
    errors: int
    contacts: List[ContactResponseDTO]


class IngestContactsUseCase:
    """
    Use Case: Ingest contacts from external source.

    Steps:
    1. Validate source exists
    2. Deduplicate contacts (email hash)
    3. Auto-tag contacts
    4. Batch insert
    5. Publish events
    """

    def __init__(
        self,
        uow: IUnitOfWork,
        event_bus: IEventBus,
        auto_tagger: AutoTagger,
        deduplicator: Deduplicator,
        mapper: ContactMapper
    ):
        self.uow = uow
        self.event_bus = event_bus
        self.auto_tagger = auto_tagger
        self.deduplicator = deduplicator
        self.mapper = mapper

    async def execute(self, command: IngestContactsCommand) -> IngestContactsResult:
        """Execute use case."""

        async with self.uow:
            # 1. Validate source exists
            source = await self.uow.data_sources.get_by_source_id(
                command.source_id,
                command.tenant_id
            )

            if not source:
                raise DataSourceNotFoundError(
                    f"Source {command.source_id} not found"
                )

            # 2. Convert DTOs to entities
            entities = [
                self.mapper.from_dto(dto, command.tenant_id, command.source_id)
                for dto in command.contacts
            ]

            # 3. Deduplicate
            unique_contacts, duplicates = await self.deduplicator.deduplicate(
                entities,
                command.tenant_id
            )

            # 4. Auto-tag
            if command.auto_tag:
                for contact in unique_contacts:
                    tags = self.auto_tagger.auto_tag_contact(contact)
                    contact.add_tags(tags)

            # 5. Batch insert
            try:
                inserted = await self.uow.contacts.batch_insert(unique_contacts)
                await self.uow.commit()

                # 6. Publish events
                for contact in inserted:
                    event = ContactIngested(
                        contact_id=contact.id,
                        email=contact.email.value,
                        tenant_id=contact.tenant_id,
                        source_id=contact.source_id
                    )
                    await self.event_bus.publish(event)

                # 7. Return result
                return IngestContactsResult(
                    batch_id=f"batch-{command.tenant_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                    accepted=len(inserted),
                    duplicates=len(duplicates),
                    errors=0,
                    contacts=[self.mapper.to_dto(c) for c in inserted]
                )

            except Exception as e:
                await self.uow.rollback()
                raise ContactIngestionError(f"Failed to ingest contacts: {str(e)}")
```

---

## 6. SCALABILITÉ & PERFORMANCE

### 6.1 Horizontal Scaling Strategy

```
┌─────────────────────────────────────────────────────────────────┐
│                    LOAD BALANCER (Nginx/HAProxy)                │
└────────────────────────┬────────────────────────────────────────┘
                         │
         ┌───────────────┴───────────────┐
         │                               │
┌────────▼────────┐            ┌─────────▼────────┐
│  API Instance 1 │            │  API Instance 2  │  ... Instance N
│  (Stateless)    │            │  (Stateless)     │
└────────┬────────┘            └─────────┬────────┘
         │                               │
         └───────────────┬───────────────┘
                         │
         ┌───────────────┴───────────────────────────┐
         │                                           │
┌────────▼────────┐                        ┌─────────▼────────┐
│   PostgreSQL    │                        │   Redis Cluster  │
│   (Primary +    │                        │   (3 nodes)      │
│    Read Replicas)│                        │                  │
└─────────────────┘                        └──────────────────┘
                                                    │
                                           ┌────────▼────────┐
                                           │  RabbitMQ/Redis │
                                           │  Message Queue  │
                                           └─────────────────┘
                                                    │
                                           ┌────────▼────────┐
                                           │  Celery Workers │
                                           │  (Auto-scaling) │
                                           └─────────────────┘
```

### 6.2 Caching Strategy (Multi-Layer)

```python
# src/infrastructure/cache/cache_service.py

from typing import Optional, Callable, Any
from functools import wraps
import json
import hashlib

from redis.asyncio import Redis
from src.infrastructure.cache.cache_keys import CacheKeys


class CacheService:
    """
    Multi-layer caching strategy:

    Layer 1: Application memory (local cache)
    Layer 2: Redis (distributed cache)
    Layer 3: Database (source of truth)
    """

    def __init__(self, redis: Redis):
        self.redis = redis
        self.local_cache = {}  # Simple dict (can use LRU cache)

    async def get(self, key: str) -> Optional[Any]:
        """
        Get from cache (multi-layer):
        1. Check local cache
        2. Check Redis
        3. Return None if not found
        """
        # Layer 1: Local cache
        if key in self.local_cache:
            return self.local_cache[key]

        # Layer 2: Redis
        value = await self.redis.get(key)
        if value:
            # Store in local cache
            self.local_cache[key] = json.loads(value)
            return self.local_cache[key]

        return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int = 3600
    ) -> None:
        """
        Set in cache (both layers):
        1. Store in Redis (distributed)
        2. Store in local cache
        """
        # Layer 2: Redis
        await self.redis.setex(
            key,
            ttl,
            json.dumps(value, default=str)
        )

        # Layer 1: Local cache
        self.local_cache[key] = value

    async def delete(self, key: str) -> None:
        """Delete from both layers."""
        await self.redis.delete(key)
        self.local_cache.pop(key, None)

    async def invalidate_pattern(self, pattern: str) -> None:
        """Invalidate all keys matching pattern."""
        keys = await self.redis.keys(pattern)
        if keys:
            await self.redis.delete(*keys)

        # Clear local cache (simple approach: clear all)
        self.local_cache.clear()


def cached(
    key_pattern: str,
    ttl: int = 3600,
    key_builder: Optional[Callable] = None
):
    """
    Decorator for caching method results.

    Usage:
        @cached(key_pattern="contact:{tenant_id}:{contact_id}", ttl=3600)
        async def get_contact(self, tenant_id: str, contact_id: str):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                # Default: hash function name + args
                params = json.dumps({'args': args, 'kwargs': kwargs}, default=str)
                params_hash = hashlib.md5(params.encode()).hexdigest()
                cache_key = f"{func.__name__}:{params_hash}"

            # Try cache
            cached_value = await self.cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            # Execute function
            result = await func(self, *args, **kwargs)

            # Store in cache
            await self.cache.set(cache_key, result, ttl)

            return result

        return wrapper
    return decorator
```

```python
# src/infrastructure/cache/cache_keys.py

class CacheKeys:
    """Cache key patterns."""

    # Contacts
    CONTACT_BY_ID = "contact:{tenant_id}:{contact_id}"
    CONTACT_BY_EMAIL = "contact:email:{tenant_id}:{email_hash}"
    CONTACTS_BY_TAGS = "contacts:tags:{tenant_id}:{tags_hash}"

    # Campaigns
    CAMPAIGN_BY_ID = "campaign:{tenant_id}:{campaign_id}"
    CAMPAIGN_STATS = "campaign:stats:{campaign_id}"

    # Templates
    TEMPLATE_BY_ID = "template:{template_id}"
    TEMPLATE_SELECTOR = "template:selector:{tenant_id}:{category}:{language}"

    # Tags
    TAGS_BY_TENANT = "tags:{tenant_id}"
    TAG_BY_SLUG = "tag:{tenant_id}:{slug}"

    # MailWizz
    MAILWIZZ_INSTANCE = "mailwizz:{instance_id}"

    # TTLs (seconds)
    TTL_SHORT = 300      # 5 minutes
    TTL_MEDIUM = 3600    # 1 hour
    TTL_LONG = 86400     # 24 hours
```

### 6.3 Database Performance

```python
# src/infrastructure/persistence/database.py

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession
)
from sqlalchemy.pool import NullPool, AsyncAdaptedQueuePool

from src.shared.config import settings


def create_database_engine():
    """
    Create database engine with optimizations:

    - Connection pooling (20 connections)
    - Statement caching
    - Echo SQL in development
    """

    engine = create_async_engine(
        settings.DATABASE_URL,

        # Connection pooling
        poolclass=AsyncAdaptedQueuePool,
        pool_size=20,              # Number of persistent connections
        max_overflow=10,           # Extra connections when pool full
        pool_pre_ping=True,        # Test connections before use
        pool_recycle=3600,         # Recycle connections after 1h

        # Performance
        echo=settings.DEBUG,       # Log SQL in development
        future=True,

        # Async
        connect_args={
            "server_settings": {
                "application_name": "email-engine",
                "jit": "on"        # JIT compilation for complex queries
            }
        }
    )

    return engine


# Create session factory
engine = create_database_engine()
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)
```

```sql
-- Database indexes for performance
-- src/infrastructure/persistence/migrations/versions/2026_02_16_performance_indexes.sql

-- Contacts: Composite indexes for common queries
CREATE INDEX CONCURRENTLY idx_contacts_tenant_status
    ON contacts(tenant_id, status)
    WHERE deleted_at IS NULL;

CREATE INDEX CONCURRENTLY idx_contacts_tenant_category_language
    ON contacts(tenant_id, category, language)
    WHERE status = 'validated';

CREATE INDEX CONCURRENTLY idx_contacts_source_created
    ON contacts(source_id, created_at DESC)
    WHERE deleted_at IS NULL;

-- GIN index for tags (array contains)
CREATE INDEX CONCURRENTLY idx_contacts_tags_gin
    ON contacts USING GIN (tags);

-- Full-text search on company/name (optionnel)
CREATE INDEX CONCURRENTLY idx_contacts_search
    ON contacts USING GIN (
        to_tsvector('english',
            COALESCE(first_name, '') || ' ' ||
            COALESCE(last_name, '') || ' ' ||
            COALESCE(company, '')
        )
    );

-- Campaigns: Status + scheduling
CREATE INDEX CONCURRENTLY idx_campaigns_tenant_status_scheduled
    ON campaigns(tenant_id, status, scheduled_at)
    WHERE scheduled_at IS NOT NULL;

-- Contact Events: Fast time-series queries
CREATE INDEX CONCURRENTLY idx_contact_events_contact_timestamp
    ON contact_events(contact_id, timestamp DESC);

CREATE INDEX CONCURRENTLY idx_contact_events_campaign_event_type
    ON contact_events(campaign_id, event_type, timestamp DESC);

-- Partitioning contact_events by date (for large scale)
CREATE TABLE contact_events_2026_02 PARTITION OF contact_events
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
```

### 6.4 Async Processing (Celery)

```python
# src/infrastructure/background/celery_app.py

from celery import Celery
from src.shared.config import settings

celery_app = Celery(
    'email-engine',
    broker=settings.CELERY_BROKER_URL,      # Redis/RabbitMQ
    backend=settings.CELERY_RESULT_BACKEND   # Redis
)

celery_app.conf.update(
    # Task routing
    task_routes={
        'src.infrastructure.background.tasks.contact_tasks.*': {'queue': 'contacts'},
        'src.infrastructure.background.tasks.campaign_tasks.*': {'queue': 'campaigns'},
        'src.infrastructure.background.tasks.mailwizz_tasks.*': {'queue': 'mailwizz'},
    },

    # Concurrency
    worker_concurrency=10,
    worker_prefetch_multiplier=4,

    # Serialization
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',

    # Time limits
    task_soft_time_limit=300,    # 5 minutes
    task_time_limit=600,          # 10 minutes hard limit

    # Retries
    task_acks_late=True,
    task_reject_on_worker_lost=True,

    # Results
    result_expires=3600,          # 1 hour

    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
)
```

```python
# src/infrastructure/background/tasks/contact_tasks.py

from celery import group
from src.infrastructure.background.celery_app import celery_app
from src.application.use_cases.contacts.validate_contact import ValidateContactUseCase
from src.infrastructure.persistence.unit_of_work import UnitOfWork


@celery_app.task(
    name='validate_contact_batch',
    bind=True,
    max_retries=3,
    default_retry_delay=60
)
def validate_contact_batch(self, contact_ids: list):
    """
    Validate batch of contacts (async task).

    Executed by Celery worker in background.
    """
    try:
        # Create task group (parallel execution)
        job = group(
            validate_single_contact.s(contact_id)
            for contact_id in contact_ids
        )

        result = job.apply_async()

        return {
            'total': len(contact_ids),
            'task_id': result.id
        }

    except Exception as exc:
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@celery_app.task(name='validate_single_contact')
async def validate_single_contact(contact_id: str):
    """Validate single contact (SMTP check)."""

    async with UnitOfWork() as uow:
        use_case = ValidateContactUseCase(uow, smtp_validator, event_bus)
        result = await use_case.execute(contact_id)
        return result.to_dict()
```

---

**Suite dans la partie 2** (fichier trop long...)

**Tu veux que je continue avec** :
7. Observabilité & Monitoring
8. Sécurité Enterprise
9. CI/CD & DevOps
10. Testing Strategy
11. Documentation
12. Migration Plan

**Ou tu veux qu'on commence l'implémentation maintenant ?** 🚀
