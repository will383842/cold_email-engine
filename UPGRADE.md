# Upgrade Guide — v1.x to v2.0

This guide helps you upgrade an existing Email Engine v1.x installation to v2.0 with minimal downtime.

## 🎯 What's Changing

### Major Changes
- ✅ **Database**: SQLite → PostgreSQL (production-ready)
- ✅ **Authentication**: Simple API key → JWT with RBAC
- ✅ **Rate Limiting**: In-memory → Redis persistence
- ✅ **MailWizz**: MySQL direct → REST API (with fallback)
- ✅ **Audit**: No audit trail → Complete compliance logging
- ✅ **CI/CD**: Manual → GitHub Actions automation

### Breaking Changes
- **Required**: `JWT_SECRET_KEY` must be set
- **Required**: `DATABASE_URL` should use PostgreSQL for production
- **Recommended**: `REDIS_URL` for production rate limiting
- **API**: Admin endpoints now require JWT with admin role

## ⏱️ Estimated Downtime

- **Minimal upgrade** (keep SQLite, add JWT): ~10 minutes
- **Full upgrade** (PostgreSQL + Redis + JWT): ~30 minutes

## 📋 Pre-Upgrade Checklist

- [ ] Backup current database: `scripts/backup-all.sh`
- [ ] Backup `.env` file
- [ ] Note current API_KEY (will still work after upgrade)
- [ ] Review CHANGELOG.md for all changes
- [ ] Test upgrade in staging environment first (recommended)

## 🚀 Upgrade Steps

### Option A: Minimal Upgrade (Keep SQLite + Add JWT)

**Best for:** Testing v2.0 features without database migration.

```bash
# 1. Stop the service
sudo systemctl stop email-engine

# 2. Backup
cd /opt/email-engine
sudo -u email-engine bash scripts/backup-all.sh

# 3. Pull latest code
cd /opt/email-engine
git pull origin main

# 4. Update dependencies
sudo -u email-engine /opt/email-engine/venv/bin/pip install -r requirements.txt

# 5. Generate JWT secret
sudo -u email-engine /opt/email-engine/venv/bin/python scripts/manage-users.py rotate-secrets
# Copy JWT_SECRET_KEY to .env (keep existing API_KEY)

# 6. Add to .env
sudo nano /opt/email-engine/.env
```

Add these lines:
```bash
JWT_SECRET_KEY=<generated-secret-from-step-5>
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Redis (optional, will fallback to in-memory if not available)
REDIS_URL=redis://localhost:6379/0
```

```bash
# 7. Run new migration (adds auth tables)
sudo -u email-engine /opt/email-engine/venv/bin/alembic upgrade head

# 8. Create admin user
sudo -u email-engine /opt/email-engine/venv/bin/python scripts/manage-users.py create-admin \
  --email admin@yourdomain.com \
  --username admin \
  --password SecurePassword123

# 9. Start service
sudo systemctl start email-engine
sudo systemctl status email-engine

# 10. Test
# Old API key still works:
curl http://localhost:8000/api/v1/ips -H "X-API-Key: $OLD_API_KEY"

# New JWT works:
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@yourdomain.com", "password": "SecurePassword123"}'
```

**Done!** You can now use both API key (legacy) and JWT authentication.

---

### Option B: Full Upgrade (PostgreSQL + Redis + JWT)

**Best for:** Production deployments requiring full features.

#### Step 1: Install PostgreSQL & Redis

```bash
# Install PostgreSQL 15
sudo apt install -y postgresql-15 postgresql-contrib-15

# Create database
sudo -u postgres psql
```

```sql
CREATE DATABASE email_engine;
CREATE USER email_engine WITH ENCRYPTED PASSWORD 'CHANGE-ME-strong-password';
GRANT ALL PRIVILEGES ON DATABASE email_engine TO email_engine;
\q
```

```bash
# Install Redis 7
sudo apt install -y redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Test
redis-cli ping  # Should return PONG
```

#### Step 2: Migrate Data (SQLite → PostgreSQL)

```bash
# Stop service
sudo systemctl stop email-engine

# Backup SQLite database
cd /opt/email-engine
sudo -u email-engine bash scripts/backup-all.sh

# Export SQLite data (we'll use alembic + manual import)
# Option 1: Use pgloader (recommended)
sudo apt install -y pgloader

# Create pgloader config
cat > /tmp/migrate.load << 'EOF'
LOAD DATABASE
  FROM sqlite:///opt/email-engine/email_engine.db
  INTO postgresql://email_engine:CHANGE-ME-strong-password@localhost/email_engine
  WITH include drop, create tables, create indexes, reset sequences
  SET work_mem to '16MB', maintenance_work_mem to '512 MB';
EOF

# Run migration
pgloader /tmp/migrate.load

# Option 2: Manual export/import (if pgloader not available)
# Export to SQL
sqlite3 /opt/email-engine/email_engine.db .dump > /tmp/sqlite_export.sql

# Import to PostgreSQL (requires some manual editing of SQL)
# ... (complex, use pgloader instead)
```

#### Step 3: Update Application

```bash
cd /opt/email-engine

# Pull latest code
git pull origin main

# Update dependencies
sudo -u email-engine /opt/email-engine/venv/bin/pip install -r requirements.txt

# Update .env
sudo nano /opt/email-engine/.env
```

Update these settings:
```bash
# Database (PostgreSQL)
DATABASE_URL=postgresql://email_engine:CHANGE-ME-strong-password@localhost/email_engine

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT (generate with: python scripts/manage-users.py rotate-secrets)
JWT_SECRET_KEY=<generated-secret>
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
```

```bash
# Run new migration (adds auth tables)
sudo -u email-engine /opt/email-engine/venv/bin/alembic upgrade head

# Create admin user
sudo -u email-engine /opt/email-engine/venv/bin/python scripts/manage-users.py create-admin \
  --email admin@yourdomain.com \
  --username admin \
  --password SecurePassword123

# Start service
sudo systemctl start email-engine
sudo systemctl status email-engine

# Verify PostgreSQL connection
sudo journalctl -u email-engine -n 50 | grep -i postgres
```

#### Step 4: Verify Migration

```bash
# Test health
curl http://localhost:8000/health

# Test JWT login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@yourdomain.com", "password": "SecurePassword123"}'

# Save token
export TOKEN="<access_token_from_response>"

# Test protected endpoint
curl http://localhost:8000/api/v1/ips -H "Authorization: Bearer $TOKEN"

# Test metrics
curl http://localhost:8000/metrics

# Check audit logs (admin only)
curl http://localhost:8000/api/v1/audit/logs -H "Authorization: Bearer $TOKEN"
```

#### Step 5: Cleanup

```bash
# If everything works, remove old SQLite database
cd /opt/email-engine
sudo -u email-engine mv email_engine.db email_engine.db.old

# Keep backup for 30 days, then delete
```

---

## 🔧 Post-Upgrade Configuration

### Enable MailWizz API (Recommended)

```bash
# Get API keys from MailWizz dashboard
# Settings → API Keys → Create Key

# Update .env
sudo nano /opt/email-engine/.env
```

Add:
```bash
MAILWIZZ_API_URL=http://mailwizz.yourdomain.com/api
MAILWIZZ_API_PUBLIC_KEY=<public-key>
MAILWIZZ_API_PRIVATE_KEY=<private-key>
```

```bash
# Restart
sudo systemctl restart email-engine
```

### Configure GitHub Actions CI/CD

```bash
# In your GitHub repository settings:
# Settings → Secrets and variables → Actions → New repository secret

# Add secrets:
- DATABASE_URL (PostgreSQL connection string)
- REDIS_URL
- API_KEY
- JWT_SECRET_KEY
- TELEGRAM_BOT_TOKEN
- SCRAPER_PRO_HMAC_SECRET

# Push to main/develop branch to trigger CI/CD
git push origin main
```

---

## 🔄 Rollback Plan

If upgrade fails, rollback to v1.x:

```bash
# Stop service
sudo systemctl stop email-engine

# Restore code
cd /opt/email-engine
git checkout <previous-commit-hash>

# Restore .env backup
sudo cp .env.backup .env

# Restore SQLite database
sudo -u email-engine cp backups/email_engine.db.backup email_engine.db

# Rollback migration (if needed)
sudo -u email-engine /opt/email-engine/venv/bin/alembic downgrade 001

# Start service
sudo systemctl start email-engine
```

---

## 📊 Monitoring After Upgrade

### Check Logs

```bash
# Real-time logs
sudo journalctl -u email-engine -f

# Check for errors
sudo journalctl -u email-engine -p err -n 50

# Check startup
sudo journalctl -u email-engine --since "5 minutes ago"
```

### Verify Scheduled Jobs

```bash
# Jobs should appear in logs every few minutes
sudo journalctl -u email-engine | grep -i "job_"

# Expected jobs:
# - job_health_check (every 5min)
# - job_metrics_update (every 1min)
# - job_sync_warmup_quotas (every 1h) ← NEW
# - job_retry_queue (every 2min)
# - job_blacklist_check (every 4h)
```

### Test Warmup Quota Sync

```bash
# Check logs for sync job
sudo journalctl -u email-engine | grep "sync_warmup_quotas"

# Should see:
# job_sync_warmup_quotas_complete synced=X total=Y
```

---

## 🆘 Troubleshooting

### JWT_SECRET_KEY not set

**Error:** `FATAL: JWT_SECRET_KEY is set to the default placeholder`

**Fix:**
```bash
python scripts/manage-users.py rotate-secrets
# Copy JWT_SECRET_KEY to .env
sudo systemctl restart email-engine
```

### PostgreSQL connection failed

**Error:** `could not connect to server: Connection refused`

**Fix:**
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Check connection string
psql -h localhost -U email_engine -d email_engine -W

# Check .env DATABASE_URL matches
```

### Redis connection failed

**Error:** `Error connecting to Redis`

**Fix:**
```bash
# Check Redis is running
sudo systemctl status redis-server

# Test connection
redis-cli ping

# Application will fallback to in-memory if Redis unavailable (dev mode)
```

### Migration failed

**Error:** `alembic.util.exc.CommandError: Can't locate revision identified by '001'`

**Fix:**
```bash
# Check alembic version
sudo -u email-engine /opt/email-engine/venv/bin/alembic current

# Show available migrations
sudo -u email-engine /opt/email-engine/venv/bin/alembic history

# Force upgrade to head
sudo -u email-engine /opt/email-engine/venv/bin/alembic upgrade head --sql > migration.sql
# Review migration.sql, then apply manually or with alembic
```

---

## 📞 Support

If you encounter issues during upgrade:

1. Check logs: `sudo journalctl -u email-engine -f`
2. Review [CHANGELOG.md](CHANGELOG.md) for breaking changes
3. Consult [DEPLOY.md](DEPLOY.md) for production setup
4. Open GitHub issue with error details

---

## ✅ Upgrade Complete!

After successful upgrade, you should have:

- ✅ PostgreSQL database (or SQLite for dev)
- ✅ Redis for rate limiting (or in-memory fallback)
- ✅ JWT authentication working
- ✅ Admin user created
- ✅ Audit logging active
- ✅ MailWizz API integration (optional)
- ✅ Hourly warmup quota sync
- ✅ GitHub Actions CI/CD (optional)

Welcome to Email Engine v2.0! 🚀
