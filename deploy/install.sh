#!/usr/bin/env bash
# Email Engine — Initial server setup
set -euo pipefail

APP_DIR="/opt/email-engine"
APP_USER="email-engine"

echo "=== Email Engine Installation ==="

# Create system user
if ! id "$APP_USER" &>/dev/null; then
    useradd --system --no-create-home --shell /usr/sbin/nologin "$APP_USER"
    echo "Created user: $APP_USER"
fi

# Create app directory
mkdir -p "$APP_DIR"
cp -r . "$APP_DIR/"
chown -R "$APP_USER:$APP_USER" "$APP_DIR"

# Python venv
cd "$APP_DIR"
python3 -m venv venv
venv/bin/pip install --upgrade pip
venv/bin/pip install -r requirements.txt

# Create .env from example if missing
if [ ! -f "$APP_DIR/.env" ]; then
    cp "$APP_DIR/.env.example" "$APP_DIR/.env"
    echo ">>> Created .env from .env.example — edit it with your secrets!"
fi

# Run migrations
cd "$APP_DIR" && venv/bin/alembic upgrade head

# Install systemd service
cp deploy/email-engine.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable email-engine

echo ""
echo "=== Installation complete ==="
echo "1. Edit /opt/email-engine/.env with your secrets"
echo "2. Start: systemctl start email-engine"
echo "3. Monitoring: cd /opt/email-engine/monitoring && docker compose up -d"
