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

echo "==> Building and starting containers ($COMPOSE_FILE)"
docker compose -f "$COMPOSE_FILE" build --pull
docker compose -f "$COMPOSE_FILE" up -d --remove-orphans --wait --wait-timeout 120

echo "==> Application is up"
docker compose -f "$COMPOSE_FILE" ps
docker image prune -f
