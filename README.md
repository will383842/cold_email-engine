# Email Engine

Professional email infrastructure manager for **PowerMTA + MailWizz**. Manages IP warmup, blacklist monitoring, DNS validation, and bounce forwarding to scraper-pro.

## Features

- **IP Lifecycle Management** — State machine: ACTIVE → RETIRING → RESTING → WARMING → ACTIVE
- **6-Week Warmup** — Progressive quota increase with safety thresholds (bounce/spam rates)
- **Blacklist Monitoring** — 9 DNS blacklists checked every 4h with auto-standby activation
- **DNS Validation** — SPF, DKIM, DMARC, PTR, MX checks
- **PowerMTA Integration** — Config read/write, queue monitoring, bounce pipe
- **MailWizz Integration** — Delivery server quota management via MySQL
- **Bounce Forwarding** — HMAC-signed forwarding to scraper-pro
- **Telegram Alerts** — Critical alerts via Telegram Bot API
- **Prometheus + Grafana** — Full monitoring dashboard

## Infrastructure

```
Hetzner VDS (5 IPs dedicees)
├── PowerMTA (envoi SMTP)
├── Email Engine (FastAPI API)
└── Config: /etc/pmta/config

Hetzner VPS
├── MailWizz (dashboard + API)
├── MySQL (MailWizz DB)
└── Nginx + SSL
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

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your config
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | System health status |
| GET | `/metrics` | Prometheus metrics |
| CRUD | `/api/v1/ips` | IP management |
| CRUD | `/api/v1/domains` | Domain management |
| GET/POST | `/api/v1/warmup/plans` | Warmup management |
| GET/POST | `/api/v1/blacklists/*` | Blacklist checks |
| POST | `/api/v1/webhooks/pmta-bounce` | Bounce receiver |

## Scheduled Jobs

| Job | Frequency | Description |
|-----|-----------|-------------|
| Health Check | 5 min | PowerMTA, disk, RAM |
| Blacklist Check | 4h | 9 DNS blacklists |
| Warmup Daily | 00:00 UTC | Phase advancement |
| Monthly Rotation | 1st 03:00 UTC | IP rotation |
| DNS Validation | 06:00 UTC | SPF/DKIM/DMARC/PTR |
| Quarantine Check | 04:00 UTC | Release rested IPs |

## Tests

```bash
pip install -r requirements.txt
pytest tests/ -v
```

## Deployment

See [DEPLOY.md](DEPLOY.md) for full production setup instructions.
