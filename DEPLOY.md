# Email Engine — Deployment Guide

## Prerequisites

- Ubuntu 22.04+ VDS with root access (Hetzner)
- PowerMTA installed and licensed
- MailWizz installed with MySQL
- Python 3.11+
- Docker + Docker Compose (for monitoring)

## Phase 1: Infrastructure Setup (Day 1-2)

### Order

- [ ] Hetzner VDS (5 IPs dedicees)
- [ ] Hetzner VPS (MailWizz)
- [ ] 3 domaines cold-outreach-X.com (~10EUR/an chacun)
- [ ] Licence PowerMTA

### Configure DNS (wait 24-48h propagation)

- [ ] DNS pour trans.mail-ulixai.com (voir dns/dns-templates.md)
- [ ] DNS pour news.sos-expat.com
- [ ] DNS pour cold-outreach-1.com
- [ ] DNS pour cold-outreach-2.com
- [ ] DNS pour cold-outreach-3.com

## Phase 2: PowerMTA (Day 3-4)

```bash
ssh root@VDS_IP

# System
apt update && apt upgrade -y
apt install -y bc host curl wget

# Install PowerMTA (follow Port25 guide)
# Copy config
scp powermta/config root@VDS_IP:/etc/pmta/config

# Generate DKIM
scp scripts/generate-dkim.sh root@VDS_IP:/root/scripts/
chmod +x /root/scripts/generate-dkim.sh
/root/scripts/generate-dkim.sh
# -> Note public keys, add to DNS

# Configure PTR at Hetzner (admin panel)
# IP1 -> trans.mail-ulixai.com
# IP2 -> news.sos-expat.com
# IP3 -> cold-outreach-1.com
# IP4 -> cold-outreach-2.com
# IP5 -> cold-outreach-3.com

# Start
systemctl start powermta
systemctl enable powermta
pmta show status
```

## Phase 3: MailWizz (Day 5-6)

Follow mailwizz/INSTALL.md

## Phase 4: Connect MailWizz -> PowerMTA (Day 7)

- [ ] Create 3 Delivery Servers in MailWizz
- [ ] Create lists (SOS-Expat + Ulixai)
- [ ] Create API keys
- [ ] Test email send

## Phase 5: Email Engine API (Automated)

```bash
# Clone the repo
git clone <repo> /opt/email-engine
cd /opt/email-engine

# Run installer (creates user, venv, migrations, systemd service)
sudo bash deploy/install.sh

# Edit configuration
sudo nano /opt/email-engine/.env

# Start the service
sudo systemctl start email-engine
```

### PowerMTA Bounce Pipe

Add to `/etc/pmta/config` to pipe bounces to email-engine:

```
<acct-file /dev/null>
    records b
    map-header-to-column bounce *
</acct-file>

<acct-file |/opt/email-engine/scripts/bounce-pipe.sh>
    records b
    map-header-to-column bounce *
</acct-file>
```

## Phase 6: Operational Scripts (Day 8)

```bash
# Copy scripts to VDS
scp scripts/*.sh root@VDS_IP:/root/scripts/
ssh root@VDS_IP "chmod +x /root/scripts/*.sh"

# Configure cron
ssh root@VDS_IP "crontab -e"
# Add:
# 0 2 * * * /root/scripts/backup-all.sh
# 0 */4 * * * /root/scripts/check-blacklists.sh
# 0 0 * * * /root/scripts/warmup-daily-adjust.sh
# */5 * * * * /root/scripts/health-check.sh
# 0 3 1 * * /root/scripts/ip-rotation.sh
```

## Phase 7: Monitoring Stack

```bash
cd /opt/email-engine/monitoring
docker compose up -d
```

- Prometheus: http://server:9090
- Grafana: http://server:3000 (admin/admin)
- Import alerts from `monitoring/grafana-alerts.yml`
- Configure Telegram bot for alerts

## Updates

```bash
sudo bash /opt/email-engine/deploy/update.sh
```

## Service Management

```bash
sudo systemctl status email-engine
sudo systemctl restart email-engine
sudo journalctl -u email-engine -f
```

## API Usage

All API endpoints require `X-API-Key` header (except `/health` and `/metrics`).

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

# Prometheus metrics
curl http://localhost:8000/metrics
```

## Final Tests (Day 9-10)

```bash
# Test 1: Mail-Tester (score > 9/10)
echo "Test" | mail -s "Test" test-xxx@mail-tester.com

# Test 2: DKIM (send to Gmail, check headers)
# DKIM=pass expected

# Test 3: Blacklist check
/root/scripts/check-blacklists.sh
# 0 blacklists expected

# Test 4: Monitoring
# Verify Grafana shows metrics

# Test 5: Health check
/root/scripts/health-check.sh
```

## Checklist GO/NO-GO

- [ ] DNS propagated (24h+)
- [ ] PowerMTA running
- [ ] MailWizz accessible HTTPS
- [ ] Delivery Servers active
- [ ] Mail-Tester > 9/10
- [ ] 0 IP blacklisted
- [ ] Monitoring operational
- [ ] Telegram alerts OK
- [ ] Backups configured
- [ ] Warm-up plan created
- [ ] Email Engine API responding

**If ALL OK -> GO PRODUCTION**
