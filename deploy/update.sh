#!/usr/bin/env bash
# Email Engine — Safe update with rollback
set -euo pipefail

APP_DIR="/opt/email-engine"
BACKUP_DIR="/backups/pre-update-$(date +%Y%m%d-%H%M%S)"

echo "=== Email Engine Update ==="

cd "$APP_DIR"

# 1. Backup current state
echo "Creating pre-update backup at $BACKUP_DIR..."
mkdir -p "$BACKUP_DIR"
git rev-parse HEAD > "$BACKUP_DIR/git-commit.txt"
cp email_engine.db "$BACKUP_DIR/" 2>/dev/null || true
echo "Backup created"

# 2. Pull latest code
PREVIOUS_COMMIT=$(git rev-parse HEAD)
git pull origin main || {
    echo "ERROR: git pull failed, nothing changed"
    exit 1
}
NEW_COMMIT=$(git rev-parse HEAD)

if [ "$PREVIOUS_COMMIT" = "$NEW_COMMIT" ]; then
    echo "Already up to date, no changes"
    rmdir "$BACKUP_DIR" 2>/dev/null || true
    exit 0
fi

echo "Updating: ${PREVIOUS_COMMIT:0:8} -> ${NEW_COMMIT:0:8}"

# 3. Update dependencies
echo "Installing dependencies..."
venv/bin/pip install -q -r requirements.txt || {
    echo "ERROR: pip install failed, rolling back..."
    git reset --hard "$PREVIOUS_COMMIT"
    echo "Rolled back to $PREVIOUS_COMMIT"
    exit 1
}

# 4. Run migrations
echo "Running migrations..."
venv/bin/alembic upgrade head || {
    echo "ERROR: migrations failed"
    echo "DB backup at: $BACKUP_DIR/email_engine.db"
    echo "Code rolled back, manual DB fix may be needed"
    git reset --hard "$PREVIOUS_COMMIT"
    exit 1
}

# 5. Restart service
echo "Restarting service..."
systemctl restart email-engine
sleep 3

# 6. Health check
if systemctl is-active --quiet email-engine; then
    echo "=== Update successful: ${PREVIOUS_COMMIT:0:8} -> ${NEW_COMMIT:0:8} ==="
    systemctl status email-engine --no-pager
else
    echo "ERROR: Service failed to start after update!"
    echo "Rolling back to $PREVIOUS_COMMIT..."
    git reset --hard "$PREVIOUS_COMMIT"
    venv/bin/pip install -q -r requirements.txt
    systemctl restart email-engine
    echo "Rolled back. DB backup at: $BACKUP_DIR/email_engine.db"
    exit 1
fi
