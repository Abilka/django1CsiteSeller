#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"

if [[ ! -f "$COMPOSE_FILE" ]]; then
  echo "Compose file not found: $COMPOSE_FILE" >&2
  exit 1
fi

if [[ ! -f .env ]]; then
  echo "Missing .env in $ROOT_DIR. Copy .env.example and configure production values." >&2
  exit 1
fi

mkdir -p data persistent/media

# Однократная миграция со старой схемы: db.sqlite3 в корне проекта
if [[ -f db.sqlite3 && ! -f data/db.sqlite3 ]]; then
  echo "==> Moving legacy db.sqlite3 to data/"
  mv db.sqlite3 data/db.sqlite3
fi

echo "==> Building and starting containers ($COMPOSE_FILE)"
docker compose -f "$COMPOSE_FILE" build --pull
echo "==> Waiting for container healthcheck (migrate + collectstatic + gunicorn, up to 3 min)"
if ! docker compose -f "$COMPOSE_FILE" up -d --remove-orphans --wait --wait-timeout 180; then
  echo "==> Deploy failed. Last logs:"
  docker compose -f "$COMPOSE_FILE" logs --tail=80 web
  exit 1
fi

echo "==> Application is up"
docker compose -f "$COMPOSE_FILE" ps
docker image prune -f
