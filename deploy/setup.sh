#!/bin/bash
# Run this once on the Raspberry Pi.
# Installs all dependencies, sets up DB/Redis, configures nginx + systemd.
set -e

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CURRENT_USER="$(whoami)"
echo "==> Repo root: $REPO_DIR"
echo "==> Running as: $CURRENT_USER"

# ── System packages ──────────────────────────────────────────────────────────
echo "==> Installing system packages..."
sudo apt-get update -q
sudo apt-get install -y -q \
  python3 python3-pip python3-venv \
  postgresql postgresql-contrib \
  redis-server \
  nginx \
  git curl

# ── PostgreSQL ───────────────────────────────────────────────────────────────
echo "==> Setting up PostgreSQL..."
sudo systemctl enable --now postgresql

sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='eventintel'" | grep -q 1 || \
  sudo -u postgres psql -c "CREATE USER eventintel WITH PASSWORD 'eventintel';"
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='eventintel'" | grep -q 1 || \
  sudo -u postgres psql -c "CREATE DATABASE eventintel OWNER eventintel;"

# ── Redis ────────────────────────────────────────────────────────────────────
echo "==> Enabling Redis..."
sudo systemctl enable --now redis-server

# ── Python venv ──────────────────────────────────────────────────────────────
echo "==> Setting up Python venv..."
cd "$REPO_DIR/server"
python3 -m venv venv
./venv/bin/pip install -q --upgrade pip
./venv/bin/pip install -q -r requirements.txt

# ── Alembic migrations ───────────────────────────────────────────────────────
echo "==> Running DB migrations..."
# Run from server/ so script_location = db/migrations resolves correctly
cd "$REPO_DIR/server"
PYTHONPATH="$REPO_DIR" ./venv/bin/alembic upgrade head

# ── Ollama ───────────────────────────────────────────────────────────────────
if ! command -v ollama &>/dev/null; then
  echo "==> Installing Ollama..."
  curl -fsSL https://ollama.ai/install.sh | sh
else
  echo "==> Ollama already installed."
fi
sudo systemctl enable --now ollama
echo "==> Pulling phi3.5 model (this takes a few minutes)..."
ollama pull phi3.5:3.8b

# ── nginx ────────────────────────────────────────────────────────────────────
echo "==> Configuring nginx..."
# Write nginx config with actual paths substituted
sed "s|/home/pi/nytw-guide|$REPO_DIR|g" "$REPO_DIR/deploy/nginx.conf" | \
  sudo tee /etc/nginx/sites-available/eventintel > /dev/null
sudo ln -sf /etc/nginx/sites-available/eventintel /etc/nginx/sites-enabled/eventintel
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx

# ── systemd services ─────────────────────────────────────────────────────────
echo "==> Installing systemd services..."
# Generate service files with actual user + path substituted
for svc in eventintel-api eventintel-celery; do
  sed -e "s|/home/pi/nytw-guide|$REPO_DIR|g" \
      -e "s|User=pi|User=$CURRENT_USER|g" \
      "$REPO_DIR/deploy/${svc}.service" | \
    sudo tee /etc/systemd/system/${svc}.service > /dev/null
done

sudo systemctl daemon-reload
sudo systemctl enable --now eventintel-api eventintel-celery

echo ""
echo "✓ Setup complete."
echo "  App: http://$(hostname -I | awk '{print $1}')"
echo "  API: http://$(hostname -I | awk '{print $1}')/api"
echo ""
echo "Make sure server/.env exists. Copy from server/.env.example if not:"
echo "  cp $REPO_DIR/server/.env.example $REPO_DIR/server/.env && nano $REPO_DIR/server/.env"
