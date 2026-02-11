#!/usr/bin/env bash
# Email Engine — Update (pull + rebuild + restart)
set -euo pipefail

APP_DIR="/opt/email-engine"

echo "=== Email Engine Update ==="

cd "$APP_DIR"

# Pull latest code
git pull origin main

# Update dependencies
venv/bin/pip install -r requirements.txt

# Run migrations
venv/bin/alembic upgrade head

# Restart service
systemctl restart email-engine

echo "=== Update complete ==="
systemctl status email-engine --no-pager
