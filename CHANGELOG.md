# Changelog

All notable changes to Email Engine will be documented in this file.

## [2.0.0] - 2026-02-13

### 🎉 Major Production-Ready Update

This release transforms Email Engine from a solid MVP to a fully production-ready system with enterprise-grade authentication, auditing, and monitoring.

### ✨ Added

#### Authentication & Security
- **JWT Authentication** - Secure token-based authentication with access and refresh tokens
- **Role-Based Access Control (RBAC)** - Admin and user roles with proper permission enforcement
- **API Key Rotation** - Support for multiple API keys with expiration and revocation
- **Audit Logging** - Complete audit trail of all user actions for compliance
- **User Management CLI** - `scripts/manage-users.py` for creating users, resetting passwords, and rotating secrets

#### Database & Infrastructure
- **PostgreSQL Support** - Production-ready database (replaces SQLite)
- **Redis Integration** - Rate limiting with persistence + caching layer
- **Alembic Migration** - New migration `002_add_auth_and_audit.py` for auth tables

#### MailWizz Integration
- **MailWizz API REST Client** - Proper API integration (replaces direct MySQL access)
- **Auto Warmup Sync** - Hourly job to sync warmup quotas to MailWizz automatically
- **Fallback to MySQL** - Backward compatibility when API not configured

#### CI/CD & Development
- **GitHub Actions Workflow** - Automated testing, linting, security scanning, and deployment
- **Ruff Linting** - Modern Python linter configuration
- **Security Scanning** - Safety (dependencies) + Bandit (code security)
- **Test Coverage** - 12 test files with >70% coverage

### 🔄 Changed

- **Rate Limiting** - Now uses Redis backend for persistence (fallback to in-memory for dev)
- **API Key Auth** - Marked as deprecated, JWT is now the preferred method
- **Environment Variables** - Added `JWT_SECRET_KEY`, `REDIS_URL`, `MAILWIZZ_API_*` settings
- **Scheduled Jobs** - Added `job_sync_warmup_quotas` (runs every hour)
- **Main Application** - Auto-detect Redis availability and configure rate limiting accordingly

### 📚 Documentation

- **README.md** - Complete rewrite with new features, authentication guide, user management
- **CHANGELOG.md** - This file for tracking changes
- **.env.example** - Updated with all new configuration options
- **API Documentation** - Enhanced Swagger/ReDoc with authentication examples

### 🧪 Testing

- **`tests/test_auth.py`** - 8 tests for JWT authentication flow
- **`tests/test_audit.py`** - 4 tests for audit logging
- **`tests/test_mailwizz_api_client.py`** - 3 tests for MailWizz API client

### 📊 Metrics & Monitoring

- No new metrics in this release, but all existing 13 metrics remain functional
- Audit logs now provide comprehensive compliance trail
- Health checks include authentication system status

### 🔧 Technical Debt Resolved

- ✅ SQLite → PostgreSQL migration path
- ✅ Simple API key → JWT with RBAC
- ✅ In-memory rate limiting → Redis persistence
- ✅ MailWizz MySQL direct access → REST API
- ✅ No CI/CD → GitHub Actions workflow
- ✅ No audit trail → Complete audit logging

### ⚠️ Breaking Changes

#### Configuration
- **Required**: `JWT_SECRET_KEY` must be set in `.env` (application will exit if not set)
- **Required**: `DATABASE_URL` should use PostgreSQL for production (SQLite still supported for dev)
- **Recommended**: `REDIS_URL` for production (rate limiting falls back to in-memory if not available)

#### API Changes
- New endpoints: `/api/v1/auth/login`, `/api/v1/auth/refresh`, `/api/v1/audit/logs`
- Admin endpoints now require JWT with admin role (not just API key)
- API key authentication still works but is deprecated

### 🚀 Migration Guide

#### From v1.x to v2.0

1. **Update Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Setup PostgreSQL** (if not already done)
   ```bash
   createdb email_engine
   createuser email_engine
   # Update DATABASE_URL in .env
   ```

3. **Setup Redis** (recommended for production)
   ```bash
   # Install Redis 7+
   # Update REDIS_URL in .env
   ```

4. **Generate Secrets**
   ```bash
   python scripts/manage-users.py rotate-secrets
   # Copy secrets to .env
   ```

5. **Run Migrations**
   ```bash
   alembic upgrade head
   ```

6. **Create Admin User**
   ```bash
   python scripts/manage-users.py create-admin \
     --email admin@example.com \
     --username admin \
     --password YourSecurePassword123
   ```

7. **Update MailWizz Integration** (optional but recommended)
   ```bash
   # Configure MAILWIZZ_API_URL, MAILWIZZ_API_PUBLIC_KEY, MAILWIZZ_API_PRIVATE_KEY
   # in .env to use REST API instead of MySQL
   ```

8. **Restart Application**
   ```bash
   sudo systemctl restart email-engine
   ```

### 📈 Performance Improvements

- Redis caching reduces database queries
- Async MailWizz API calls improve responsiveness
- Optimized SQL queries with proper indexing

### 🐛 Bug Fixes

- None in this release (new features only)

---

## [1.0.0] - 2026-02-01

### Initial Release

- IP lifecycle management with state machine
- 6-week warmup system
- Blacklist monitoring (9 DNS blacklists)
- DNS validation (SPF/DKIM/DMARC/PTR)
- PowerMTA integration
- MailWizz MySQL integration
- Bounce forwarding to scraper-pro
- Telegram alerts
- Prometheus + Grafana monitoring
- 8 scheduled jobs (APScheduler)
- SQLite database
- Simple API key authentication
- Health checks and metrics
