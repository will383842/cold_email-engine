# Email Engine

Professional email infrastructure manager for **PowerMTA + MailWizz**. Manages IP warmup, blacklist monitoring, DNS validation, and bounce forwarding to scraper-pro.

## Features

### Core Functionality
- **IP Lifecycle Management** — State machine: ACTIVE → RETIRING → RESTING → WARMING → ACTIVE
- **6-Week Warmup** — Progressive quota increase with safety thresholds (bounce/spam rates)
- **Auto Warmup Sync** — Hourly synchronization of quotas to MailWizz
- **Blacklist Monitoring** — 9 DNS blacklists checked every 4h with auto-standby activation
- **DNS Validation** — SPF, DKIM, DMARC, PTR, MX checks
- **PowerMTA Integration** — Config read/write, queue monitoring, bounce pipe
- **MailWizz Integration** — REST API + MySQL fallback for quota management
- **Bounce Forwarding** — HMAC-signed forwarding to scraper-pro

### Security & Authentication
- **JWT Authentication** — Secure token-based authentication with refresh tokens
- **Role-Based Access Control (RBAC)** — Admin and user roles
- **API Key Rotation** — Support for multiple API keys with expiration
- **Audit Logging** — Complete audit trail of all actions (compliance-ready)

### Monitoring & Alerting
- **Telegram Alerts** — Critical alerts via Telegram Bot API
- **Prometheus + Grafana** — Full monitoring dashboard with 13 metrics
- **Alertmanager** — 7 alert rules with Telegram integration
- **Health Checks** — Automated system health monitoring every 5min
- **Structured Logging** — JSON logs for easy parsing and analysis

## Infrastructure

```
Production Server
├── PostgreSQL 15 (primary database)
├── Redis 7 (rate limiting + caching)
├── PowerMTA (SMTP sending)
├── Email Engine (FastAPI API)
└── Nginx (reverse proxy + SSL)

External Services
├── MailWizz (email platform + API)
└── Scraper-Pro (bounce feedback)

Monitoring Stack (Docker Compose)
├── Prometheus (metrics collection)
├── Grafana (dashboards)
└── Alertmanager (Telegram alerts)
```

## Project Structure

```
email-engine/
├── app/                # FastAPI application
│   ├── api/routes/     # API endpoints
│   ├── services/       # Business logic
│   ├── scheduler/      # APScheduler jobs
│   └── scripts/        # CLI runner
├── alembic/            # Database migrations
├── tests/              # Test suite
├── deploy/             # Systemd service + install scripts
├── monitoring/         # Prometheus + Grafana stack
├── powermta/           # PowerMTA config + DKIM
├── mailwizz/           # MailWizz install notes
├── scripts/            # Operational bash scripts
├── dns/                # DNS templates
└── backups/            # Backup scripts
```

## Quick Start

### Development Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with your config (PostgreSQL, Redis, JWT secrets, etc.)

# Run migrations
alembic upgrade head

# Create admin user
python scripts/manage-users.py create-admin \
  --email admin@example.com \
  --username admin \
  --password your-secure-password

# Start server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Production Deployment

See [DEPLOY.md](DEPLOY.md) for complete production setup with PostgreSQL, Redis, systemd, and nginx.

### Docker (Optional)

```bash
docker-compose up -d  # Starts monitoring stack (Prometheus + Grafana + Alertmanager)
```

## API Endpoints

### Public Endpoints (no auth)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | System health status |
| GET | `/metrics` | Prometheus metrics |
| GET | `/docs` | Swagger UI (API documentation) |
| GET | `/redoc` | ReDoc (alternative docs) |

### Authentication
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/login` | Login with email/password → JWT tokens |
| POST | `/api/v1/auth/refresh` | Refresh access token |

### Protected Endpoints (JWT required)
| Method | Path | Description |
|--------|------|-------------|
| CRUD | `/api/v1/ips` | IP management |
| CRUD | `/api/v1/domains` | Domain management |
| GET/POST | `/api/v1/warmup/plans` | Warmup management |
| GET/POST | `/api/v1/blacklists/*` | Blacklist checks |
| POST | `/api/v1/webhooks/pmta-bounce` | Bounce receiver (API key or JWT) |
| POST | `/api/v1/validation/emails` | Email validation |

### Admin Endpoints (JWT admin role required)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/audit/logs` | Audit trail (compliance) |

## Scheduled Jobs

| Job | Frequency | Description |
|-----|-----------|-------------|
| Health Check | 5 min | PowerMTA, disk, RAM monitoring |
| Blacklist Check | 4h | 9 DNS blacklists check |
| Warmup Daily | 00:00 UTC | Phase advancement + safety checks |
| **Sync Warmup Quotas** | 1h | **Sync quotas to MailWizz (new)** |
| Monthly Rotation | 1st 03:00 UTC | IP rotation ACTIVE→RETIRING |
| DNS Validation | 06:00 UTC | SPF/DKIM/DMARC/PTR validation |
| Quarantine Check | 04:00 UTC | Release IPs from quarantine |
| Metrics Update | 1 min | Update Prometheus gauges |
| Retry Queue | 2 min | Retry failed scraper-pro calls |

## User Management

```bash
# Create admin user
python scripts/manage-users.py create-admin \
  --email admin@example.com \
  --username admin \
  --password SecurePassword123

# Create regular user
python scripts/manage-users.py create-user \
  --email user@example.com \
  --username user \
  --password Password123

# List all users
python scripts/manage-users.py list

# Reset password
python scripts/manage-users.py reset-password \
  --email admin@example.com \
  --password NewPassword123

# Generate new secrets for rotation
python scripts/manage-users.py rotate-secrets
```

## Tests

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Run specific test file
pytest tests/test_auth.py -v
```

## CI/CD

GitHub Actions workflow runs automatically on push:
- ✅ Lint with Ruff
- ✅ Run tests with PostgreSQL + Redis
- ✅ Security scan (Safety + Bandit)
- ✅ Build check
- 🚀 Auto-deploy to staging/production (configure in workflow)

## Production Readiness

### Security Checklist
- ✅ JWT authentication with refresh tokens
- ✅ Role-based access control (RBAC)
- ✅ API key rotation support
- ✅ Audit logging for compliance
- ✅ Rate limiting with Redis persistence
- ✅ HTTPS via nginx reverse proxy
- ✅ Secrets via environment variables
- ✅ Systemd security hardening

### Database
- ✅ PostgreSQL 15 (production-ready)
- ✅ Alembic migrations
- ✅ Backup scripts

### Monitoring
- ✅ Prometheus metrics (13 metrics)
- ✅ Grafana dashboards
- ✅ Alertmanager → Telegram
- ✅ Structured JSON logs
- ✅ Health checks every 5min

## Documentation

- **[DEPLOY.md](DEPLOY.md)** — Complete production deployment guide
- **[/docs](http://localhost:8000/docs)** — Interactive API documentation (Swagger UI)
- **[/redoc](http://localhost:8000/redoc)** — Alternative API docs (ReDoc)
- **[dns/dns-templates.md](dns/dns-templates.md)** — DNS configuration templates

## License

Proprietary — All rights reserved.

## Support

For issues and questions, contact the development team.
