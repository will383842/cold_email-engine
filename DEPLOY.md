# Email Engine — Deployment Guide (Cold Email)

## Prerequisites

- Ubuntu 22.04+ VDS with root access (Hetzner)
- PowerMTA installed and licensed
- MailWizz installed with MySQL
- scraper-pro running (PostgreSQL + Redis)
- Python 3.11+
- **PostgreSQL 15+** (production database)
- **Redis 7+** (rate limiting + caching)
- nginx + certbot (for HTTPS)
- Docker + Docker Compose (for monitoring)

## Phase 1: Infrastructure Setup (Day 1-2)

### Order

- [ ] Hetzner VDS (5 dedicated IPs)
- [ ] Hetzner VPS (MailWizz)
- [ ] 3 domains cold-outreach-X.com (~10EUR/year each)
- [ ] PowerMTA license

### Configure DNS (wait 24-48h propagation)

- [ ] DNS for trans.mail-ulixai.com (see dns/dns-templates.md)
- [ ] DNS for news.sos-expat.com
- [ ] DNS for cold-outreach-1.com
- [ ] DNS for cold-outreach-2.com
- [ ] DNS for cold-outreach-3.com

## Phase 2: PowerMTA (Day 3-4)

```bash
ssh root@VDS_IP

# System
apt update && apt upgrade -y
apt install -y bc host curl wget

# Install PowerMTA (follow Port25 guide)

# IMPORTANT: Replace ALL placeholders in config BEFORE copying
# Edit powermta/config and replace:
#   IP1_ADDRESS         -> your transactional IP
#   IP2_ADDRESS         -> your marketing IP
#   IP3_ADDRESS         -> your cold active IP
#   IP4_ADDRESS         -> your standby-1 IP
#   IP5_ADDRESS         -> your standby-2 IP
#   VPS_MAILWIZZ_IP     -> your MailWizz server IP
#   CHANGE_ME_PASSWORD  -> your SMTP relay password
#   YOUR_DOMAIN.com     -> your postmaster domain

# Copy ALL PowerMTA configuration files
scp powermta/config root@VDS_IP:/etc/pmta/config
scp powermta/bounce-classifications root@VDS_IP:/etc/pmta/bounce-classifications
scp powermta/routing-domains root@VDS_IP:/etc/pmta/routing-domains

# Generate DKIM keys
scp scripts/generate-dkim.sh root@VDS_IP:/opt/email-engine/scripts/
ssh root@VDS_IP "chmod +x /opt/email-engine/scripts/generate-dkim.sh"
ssh root@VDS_IP "/opt/email-engine/scripts/generate-dkim.sh"
# -> Note public keys, add to DNS as TXT records

# Configure PTR records at Hetzner (admin panel)
# IP1 -> trans.mail-ulixai.com
# IP2 -> news.sos-expat.com
# IP3 -> cold-outreach-1.com
# IP4 -> cold-outreach-2.com
# IP5 -> cold-outreach-3.com

# Verify config syntax before starting
pmta check

# Start
systemctl start powermta
systemctl enable powermta
pmta show status
```

### PowerMTA Files Reference

| File | Deploy to | Description |
|------|-----------|-------------|
| `powermta/config` | `/etc/pmta/config` | Main config: VMTAs, pools, ISP throttling, backoff, bounce/delivery pipes, auth, DKIM |
| `powermta/bounce-classifications` | `/etc/pmta/bounce-classifications` | 2785 SMTP response patterns for bounce categorization |
| `powermta/routing-domains` | `/etc/pmta/routing-domains` | 15 ISP MX-to-domain regex patterns for correct throttling |

### ISP Throttling (Cold Email — Conservative)

The config includes per-ISP rate limits tuned for cold outreach:

| ISP | Rate | Notes |
|-----|------|-------|
| Gmail | 50/h | Extremely strict on cold |
| Hotmail/Outlook | 50/h, 1 conn | Connection limit enforced |
| Yahoo | 30/h, 2 msg/conn | Very strict policy |
| AOL | 50/h | Complaint-sensitive |
| French ISPs (Orange, Free, SFR) | 30/h | Very strict |
| German ISPs (T-Online, Web.de) | 30/h | Strict |
| Other US ISPs | 50/h | Conservative default |
| All other domains | 500/h | Global default |

### Backoff Auto-Recovery

When PowerMTA detects an ISP blocking pattern (80+ patterns), it:
1. Drops to 1 msg/min (backoff mode)
2. Retries every 20 minutes
3. Auto-recovers after 1 hour
4. Returns to normal rate after successful delivery

## Phase 2.5: PostgreSQL & Redis Setup (Production)

### Install PostgreSQL 15

```bash
ssh root@VDS_IP

# Install PostgreSQL 15
apt install -y postgresql-15 postgresql-contrib-15

# Start and enable
systemctl start postgresql
systemctl enable postgresql

# Create database and user
sudo -u postgres psql
```

```sql
CREATE DATABASE email_engine;
CREATE USER email_engine WITH ENCRYPTED PASSWORD 'CHANGE-ME-strong-password';
GRANT ALL PRIVILEGES ON DATABASE email_engine TO email_engine;
\q
```

```bash
# Test connection
psql -h localhost -U email_engine -d email_engine -W
```

### Install Redis 7

```bash
# Install Redis 7
apt install -y redis-server

# Configure Redis
nano /etc/redis/redis.conf
# Set: maxmemory 512mb
# Set: maxmemory-policy allkeys-lru

# Start and enable
systemctl restart redis-server
systemctl enable redis-server

# Test
redis-cli ping
# Should return: PONG
```

### Security Hardening

```bash
# PostgreSQL: restrict to localhost only
nano /etc/postgresql/15/main/postgresql.conf
# Set: listen_addresses = 'localhost'

# Firewall: only allow localhost connections
ufw allow from 127.0.0.1 to any port 5432
ufw allow from 127.0.0.1 to any port 6379
```

## Phase 3: MailWizz (Day 5-6)

Follow mailwizz/INSTALL.md

## Phase 4: Connect MailWizz -> PowerMTA (Day 7)

- [ ] Create delivery servers in MailWizz (cold-outreach domains)
- [ ] Configure SMTP relay: host=VDS_IP, port=2525, user=mailwizz
- [ ] Create cold email lists
- [ ] Test email send (check DKIM/SPF headers)

## Phase 5: Email Engine API (Day 8)

```bash
# Clone the repo
git clone <repo> /opt/email-engine
cd /opt/email-engine

# Run installer (creates user, venv, migrations, logrotate, systemd service)
sudo bash deploy/install.sh

# Edit configuration (REQUIRED before starting)
sudo nano /opt/email-engine/.env
```

**Required configuration (.env):**

```bash
# API & JWT (REQUIRED — generate with: python scripts/manage-users.py rotate-secrets)
API_KEY=<generated-api-key-64-chars>
JWT_SECRET_KEY=<generated-jwt-secret-128-chars>

# Database (PostgreSQL for production)
DATABASE_URL=postgresql://email_engine:YOUR_PASSWORD@localhost/email_engine

# Redis (production)
REDIS_URL=redis://localhost:6379/0

# Telegram Alerts (RECOMMENDED)
TELEGRAM_BOT_TOKEN=<your-bot-token>
TELEGRAM_CHAT_ID=<your-chat-id>

# Scraper-Pro Integration (RECOMMENDED)
SCRAPER_PRO_BOUNCE_URL=http://SCRAPER_IP:8000/api/v1/contacts/bounce-feedback
SCRAPER_PRO_DELIVERY_URL=http://SCRAPER_IP:8000/api/v1/contacts/delivery-feedback
SCRAPER_PRO_HMAC_SECRET=<shared-secret-with-scraper-pro>

# MailWizz API (RECOMMENDED — cleaner than MySQL)
MAILWIZZ_API_URL=http://mailwizz.local/api
MAILWIZZ_API_PUBLIC_KEY=<mailwizz-public-key>
MAILWIZZ_API_PRIVATE_KEY=<mailwizz-private-key>

# MailWizz MySQL (FALLBACK if API not configured)
MAILWIZZ_DB_HOST=MAILWIZZ_VPS_IP
MAILWIZZ_DB_PORT=3306
MAILWIZZ_DB_USER=mailwizz
MAILWIZZ_DB_PASSWORD=<mailwizz-db-password>
MAILWIZZ_DB_NAME=mailwizz
```

**Generate secrets:**

```bash
cd /opt/email-engine
sudo -u email-engine python3 scripts/manage-users.py rotate-secrets
# Copy generated secrets to .env
```

**Run database migrations:**

```bash
cd /opt/email-engine
sudo -u email-engine /opt/email-engine/venv/bin/alembic upgrade head
```

**Create admin user:**

```bash
cd /opt/email-engine
sudo -u email-engine /opt/email-engine/venv/bin/python scripts/manage-users.py create-admin \
  --email admin@yourdomain.com \
  --username admin \
  --password YourSecurePassword123
```

**Start the service:**

```bash
sudo systemctl start email-engine
sudo systemctl enable email-engine
sudo systemctl status email-engine

# Check logs
sudo journalctl -u email-engine -f
```

**Test API with JWT:**

```bash
# Login to get JWT tokens
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@yourdomain.com", "password": "YourSecurePassword123"}'

# Save access_token from response, then use it:
export TOKEN="<access_token>"

# Test protected endpoint
curl http://localhost:8000/api/v1/ips \
  -H "Authorization: Bearer $TOKEN"
```

### Nginx Reverse Proxy (RECOMMENDED)

```bash
sudo apt install -y nginx certbot python3-certbot-nginx

# Copy and edit nginx config
sudo cp /opt/email-engine/deploy/nginx.conf /etc/nginx/sites-available/email-engine
sudo nano /etc/nginx/sites-available/email-engine
# -> Replace YOUR_DOMAIN with your actual domain

sudo ln -s /etc/nginx/sites-available/email-engine /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# Get SSL certificate
sudo certbot --nginx -d engine.YOUR_DOMAIN
```

The service binds to `127.0.0.1:8000` — only accessible via nginx.
Nginx restricts `/metrics` to localhost and Docker network.

### Accounting Pipes (already in config)

The `powermta/config` includes two accounting pipes:

**Bounce pipe** — classifies bounces and forwards to scraper-pro:
```
<acct-file |/opt/email-engine/scripts/bounce-pipe.sh>
    records b
    map-header-to-column bounce *
</acct-file>
```

**Delivery pipe** — reports delivery counts per domain to scraper-pro:
```
<acct-file |/opt/email-engine/scripts/delivery-pipe.sh>
    records d
    map-header-to-column delivery *
</acct-file>
```

Both pipes forward data to Email Engine API, which relays to scraper-pro with HMAC-SHA256 signature. scraper-pro uses delivery counts to calculate accurate per-domain bounce rates.

### Email Validation (Pre-Send)

Before importing purchased lists into MailWizz, validate emails:

```bash
curl -X POST http://localhost:8000/api/v1/validation/emails \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"emails": ["test@gmail.com", "fake@nonexistent.xyz"]}'

# Response:
# {"total": 2, "valid": 1, "invalid": 1, "results": [...]}
```

Checks: syntax, DNS MX records, blacklisted prefixes (noreply, admin...), disposable domains.
Rate limited to 10 requests/minute, max 10,000 emails per request.

## Phase 6: Operational Scripts

```bash
# Copy scripts to VDS
scp scripts/*.sh root@VDS_IP:/opt/email-engine/scripts/
ssh root@VDS_IP "chmod +x /opt/email-engine/scripts/*.sh"
```

### Scheduling: APScheduler vs Cron

**Email Engine uses APScheduler** for all recurring jobs (health checks, blacklist
checks, warmup, IP rotation, DNS validation, quarantine, metrics). These run
automatically when the service is running.

The bash scripts in `scripts/` are **standalone fallbacks** for manual use or
if APScheduler is disabled. **Do NOT add them to cron** — this would cause
duplicate execution, race conditions, and double Telegram alerts.

The **only cron job** needed is the daily backup (not handled by APScheduler):

```bash
ssh root@VDS_IP "crontab -e"
# Add only this line:
0 2 * * * /opt/email-engine/scripts/backup-all.sh >> /var/log/email-engine/backup.log 2>&1
```

### Log Rotation (installed by install.sh)

Logs are rotated daily, kept 30 days compressed:
- `/var/log/email-engine/bounce-pipe.log`
- `/var/log/email-engine/delivery-pipe.log`
- `/var/log/email-engine/backup.log`

Config: `/etc/logrotate.d/email-engine`

## Phase 7: Monitoring Stack

```bash
# Set Grafana password first
echo "GRAFANA_ADMIN_PASSWORD=$(openssl rand -hex 16)" >> /opt/email-engine/.env

cd /opt/email-engine/monitoring
docker compose up -d
```

- Prometheus: http://server:9090
- Alertmanager: http://server:9093
- Grafana: http://server:3000 (admin / your-password)

### Alertmanager -> Telegram

Alerts are routed: Prometheus -> Alertmanager -> Telegram bot.

1. Edit `monitoring/alertmanager.yml`:
   - Replace `TELEGRAM_CHAT_ID_PLACEHOLDER` with your chat ID
   - Create `/etc/alertmanager/telegram_bot_token` with your bot token
2. Alert rules are in `monitoring/alert-rules.yml`
3. Critical alerts repeat every 1h, warnings every 4h

## Updates

```bash
# Safe update with automatic rollback on failure
sudo bash /opt/email-engine/deploy/update.sh
```

The update script:
1. Backs up current code + database to `/backups/pre-update-YYYYMMDD-HHMMSS/`
2. Pulls latest code
3. Updates dependencies
4. Runs database migrations
5. Restarts service
6. Health check — auto-rollback if service fails to start

## Service Management

```bash
sudo systemctl status email-engine
sudo systemctl restart email-engine
sudo journalctl -u email-engine -f
```

## API Usage

All API endpoints require `X-API-Key` header (except `/health` and `/metrics`).
Rate limited: 60/min default, 200/min webhooks, 10/min validation.

```bash
# Health check
curl http://localhost:8000/health

# Create an IP
curl -X POST http://localhost:8000/api/v1/ips \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"address": "1.2.3.4", "hostname": "mail.example.com"}'

# List IPs
curl http://localhost:8000/api/v1/ips -H "X-API-Key: your-key"

# Check blacklists
curl -X POST http://localhost:8000/api/v1/blacklists/check/1 -H "X-API-Key: your-key"

# Validate emails before importing to MailWizz
curl -X POST http://localhost:8000/api/v1/validation/emails \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"emails": ["test@gmail.com", "info@company.com"]}'

# Prometheus metrics
curl http://localhost:8000/metrics
```

## Integration Architecture

```
Purchased Lists -> Validate (Email Engine) -> Import to MailWizz
                                                    |
                                              MailWizz sends
                                              via PowerMTA
                                                    |
                            +-----------------------+-----------------------+
                            |                                               |
                    Delivered (d)                                    Bounced (b)
                            |                                               |
                    delivery-pipe.sh                                bounce-pipe.sh
                            |                                               |
                    Email Engine                                    Email Engine
                    /pmta-delivery                                  /pmta-bounce
                            |                                               |
                    scraper-pro                                     scraper-pro
                    /delivery-feedback                              /bounce-feedback
                            |                                               |
                    Updates total_sent                        Marks contact bounced
                    per domain                               Updates domain blacklist
                            |                                               |
                            +--------> Accurate bounce rate <---------------+
                                       per domain (>10% = auto-blacklist)
```

## Final Tests (Day 9-10)

```bash
# Test 1: Mail-Tester (score > 9/10)
echo "Test" | mail -s "Test" test-xxx@mail-tester.com

# Test 2: DKIM (send to Gmail, check headers)
# DKIM=pass, SPF=pass, DMARC=pass expected

# Test 3: Blacklist check
/opt/email-engine/scripts/check-blacklists.sh
# 0 blacklists expected

# Test 4: Monitoring
# Verify Grafana shows metrics, Alertmanager is connected
curl http://localhost:9090/api/v1/rules  # Prometheus alert rules loaded
curl http://localhost:9093/api/v2/status  # Alertmanager healthy

# Test 5: Health check
curl http://localhost:8000/health
# {"status": "healthy", "issues": []}

# Test 6: Bounce pipe
# Send test bounce, verify it appears in API logs
# journalctl -u email-engine | grep "bounce_forwarded"

# Test 7: Delivery pipe
# Send test email, verify delivery feedback reaches scraper-pro
# journalctl -u email-engine | grep "delivery_forwarded"

# Test 8: Email validation
curl -X POST http://localhost:8000/api/v1/validation/emails \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"emails": ["test@gmail.com"]}'
# {"total": 1, "valid": 1, ...}

# Test 9: ISP throttling
# Send 100 emails to Gmail, verify queue shows backoff if throttled
pmta show queues gmail.com

# Test 10: Bounce classification
# Verify bounce-classifications loaded:
pmta show status | grep bounce

# Test 11: Rate limiting
# Hit the API rapidly, verify 429 responses
for i in $(seq 1 70); do curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/health; done
# Should see 429 after ~60 requests

# Test 12: nginx + HTTPS
curl https://engine.YOUR_DOMAIN/health
```

## Checklist GO/NO-GO

- [ ] DNS propagated (24h+)
- [ ] PowerMTA running (`pmta show status`)
- [ ] Bounce classifications loaded (2785 patterns)
- [ ] ISP throttling active (check `pmta show domains`)
- [ ] Backoff patterns active (`pmta show pattern-lists`)
- [ ] MailWizz accessible HTTPS
- [ ] Delivery Servers active
- [ ] Mail-Tester > 9/10
- [ ] 0 IP blacklisted
- [ ] scraper-pro running and connected (bounce + delivery feedback)
- [ ] Email validation endpoint working
- [ ] Monitoring operational (Prometheus + Alertmanager + Grafana)
- [ ] Telegram alerts OK (test by stopping PowerMTA briefly)
- [ ] nginx + HTTPS active
- [ ] Log rotation configured (`/etc/logrotate.d/email-engine`)
- [ ] Backups configured (`/backups` exists, cron added)
- [ ] Warm-up plan created via API
- [ ] Email Engine API responding
- [ ] Rate limiting active (429 on abuse)
- [ ] Bounce pipe working (test bounce forwarded to scraper-pro)
- [ ] Delivery pipe working (delivery counts forwarded to scraper-pro)

**If ALL OK -> GO PRODUCTION**
