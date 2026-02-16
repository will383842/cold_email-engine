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

# Create backup directory
mkdir -p /backups
chown "$APP_USER:$APP_USER" /backups
echo "Created /backups directory"

# Create log directory for bounce/delivery pipes
mkdir -p /var/log/email-engine
chown "$APP_USER:$APP_USER" /var/log/email-engine

# Python venv
cd "$APP_DIR"
python3 -m venv venv
venv/bin/pip install --upgrade pip
venv/bin/pip install -r requirements.txt

# Create .env from example if missing
if [ ! -f "$APP_DIR/.env" ]; then
    cp "$APP_DIR/.env.example" "$APP_DIR/.env"
    chmod 600 "$APP_DIR/.env"
    chown "$APP_USER:$APP_USER" "$APP_DIR/.env"
    echo ">>> Created .env from .env.example — edit it with your secrets!"
fi

# Run migrations with verification
echo "Running database migrations..."
if ! (cd "$APP_DIR" && venv/bin/alembic upgrade head); then
    echo "ERROR: Database migration failed. Check alembic configuration."
    exit 1
fi
echo "Migrations applied successfully"

# Make scripts executable
chmod +x "$APP_DIR"/scripts/*.sh 2>/dev/null || true

# Install logrotate config
cp deploy/logrotate /etc/logrotate.d/email-engine
echo "Installed logrotate config"

# Install systemd service
cp deploy/email-engine.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable email-engine

echo ""
echo "=== Installation complete ==="
echo ""
echo "REQUIRED — Edit secrets:"
echo "  sudo nano /opt/email-engine/.env"
echo "  (set API_KEY, TELEGRAM_BOT_TOKEN, SCRAPER_PRO_HMAC_SECRET)"
echo ""
echo "Start the service:"
echo "  sudo systemctl start email-engine"
echo ""
echo "Monitoring stack:"
echo "  cd /opt/email-engine/monitoring && docker compose up -d"
echo ""
echo "RECOMMENDED — Install nginx reverse proxy:"
echo "  sudo apt install -y nginx certbot python3-certbot-nginx"
echo "  sudo cp /opt/email-engine/deploy/nginx.conf /etc/nginx/sites-available/email-engine"
echo "  # Edit /etc/nginx/sites-available/email-engine — replace YOUR_DOMAIN"
echo "  sudo ln -s /etc/nginx/sites-available/email-engine /etc/nginx/sites-enabled/"
echo "  sudo certbot --nginx -d engine.YOUR_DOMAIN"
echo "  sudo systemctl reload nginx"
echo ""
echo "Backups — Add to crontab:"
echo "  0 2 * * * /opt/email-engine/scripts/backup-all.sh >> /var/log/email-engine/backup.log 2>&1"
