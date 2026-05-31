#!/bin/bash
# Run from Mac to push the built app and code to the Pi.
# Usage: ./deploy/sync.sh [pi-hostname-or-ip]
set -e

PI="${1:-pi.local}"
REMOTE_USER="raphaeal"
REMOTE_DIR="/home/raphaeal/nytw-guide"
LOCAL_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "==> Syncing to ${REMOTE_USER}@${PI}:${REMOTE_DIR}"

# Build the React app first
echo "==> Building PWA..."
cd "$LOCAL_ROOT/app"
npm run build

# Rsync everything except venvs, node_modules, __pycache__, .env files
rsync -avz --progress \
  --exclude='app/node_modules' \
  --exclude='app/.vite' \
  --exclude='venv/' \
  --exclude='server/venv/' \
  --exclude='**/__pycache__' \
  --exclude='**/*.pyc' \
  --exclude='**/.env' \
  --exclude='.git' \
  "$LOCAL_ROOT/" "${REMOTE_USER}@${PI}:${REMOTE_DIR}/"

echo ""
echo "✓ Sync complete."
echo ""
echo "If this is the first deploy, SSH in and run:"
echo "  ssh ${REMOTE_USER}@${PI}"
echo "  cd ${REMOTE_DIR} && bash deploy/setup.sh"
echo ""
echo "If updating an existing deploy:"
echo "  ssh ${REMOTE_USER}@${PI} 'sudo systemctl restart eventintel-api eventintel-celery'"
