#!/usr/bin/env bash
set -euo pipefail

# Первичная настройка VPS (Ubuntu/Debian).
# Запуск на сервере от root или через sudo:
#   curl -fsSL <raw-url>/scripts/server-setup.sh | sudo bash

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  echo "Run as root or with sudo." >&2
  exit 1
fi

DEPLOY_USER="${DEPLOY_USER:-deploy}"
DEPLOY_PATH="${DEPLOY_PATH:-/opt/django1CsiteSeller}"
REPO_URL="${REPO_URL:-}"

apt-get update
apt-get install -y ca-certificates curl git ufw

if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
fi

if ! id "$DEPLOY_USER" &>/dev/null; then
  useradd -m -s /bin/bash "$DEPLOY_USER"
fi

usermod -aG docker "$DEPLOY_USER"

mkdir -p "$DEPLOY_PATH"
chown -R "$DEPLOY_USER:$DEPLOY_USER" "$DEPLOY_PATH"

ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

echo "==> Server packages installed."
echo "==> Next steps:"
echo "  1. Add SSH public key for GitHub Actions to ~$DEPLOY_USER/.ssh/authorized_keys"
echo "  2. Place .env in $DEPLOY_PATH (private repo: scp .env.example from your PC)"
echo "  3. Add GitHub Actions secrets (SSH_HOST, SSH_USER, SSH_PRIVATE_KEY, DEPLOY_PATH)"
echo "  4. git push to main — Actions will rsync code and run docker compose"
echo ""
echo "Note: git clone on the server is NOT required (works with private repos)."
