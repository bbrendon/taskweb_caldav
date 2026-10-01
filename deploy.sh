#!/usr/bin/env bash
# Deploy TaskWeb to the VM: sync code + library, rebuild, restart, health-check.
#
#   ./deploy.sh                  # deploys to 10.2.2.222:/srv/taskweb_caldav
#   DEPLOY_HOST=user@host ./deploy.sh
#
# Server-only state is never overwritten: .env (secrets) and data/ (saved views).
set -euo pipefail

HOST="${DEPLOY_HOST:-10.2.2.222}"
DIR="${DEPLOY_DIR:-/srv/taskweb_caldav}"
HERE="$(cd "$(dirname "$0")" && pwd)"
LIB="${TASK_CALDAV_LIB:-$HERE/../task-caldav-lib}"

[ -f "$LIB/pyproject.toml" ] || { echo "task-caldav-lib not found at $LIB" >&2; exit 1; }
[ -f "$HERE/config/taskweb.yaml" ] || { echo "config/taskweb.yaml missing (copy taskweb.example.yaml)" >&2; exit 1; }

EXCLUDES=(
  --exclude .git/ --exclude .venv/ --exclude __pycache__/ --exclude node_modules/
  --exclude .pytest_cache/ --exclude '*.egg-info/' --exclude .DS_Store
)

echo "==> Syncing app to $HOST:$DIR"
ssh "$HOST" "mkdir -p '$DIR/data'"
rsync -az --delete "${EXCLUDES[@]}" \
  --exclude /.env --exclude /data/ --exclude /backups/ --exclude /task-caldav-lib/ \
  --exclude /frontend/dist/ --exclude /backend/app/static/ \
  "$HERE/" "$HOST:$DIR/"

echo "==> Syncing task-caldav-lib"
rsync -az --delete "${EXCLUDES[@]}" --exclude /tests/ "$LIB/" "$HOST:$DIR/task-caldav-lib/"

echo "==> Building and starting"
ssh "$HOST" bash -s -- "$DIR" <<'REMOTE'
set -euo pipefail
cd "$1"
if [ ! -f .env ]; then
  echo "!! $1/.env is missing on the server. Create it from .env.example (APP_PASSWORD_HASH, SESSION_SECRET, CALDAV_*), then rerun." >&2
  exit 1
fi
export APP_UID="$(id -u)" APP_GID="$(id -g)"
docker compose build
docker compose up -d
echo "==> Waiting for health check"
for i in $(seq 1 20); do
  if curl -fsS http://127.0.0.1:38000/api/health >/dev/null 2>&1; then
    echo "==> Up: http://$(hostname -I | awk '{print $1}'):38000"
    exit 0
  fi
  sleep 1
done
echo "!! Health check failed. Recent logs:" >&2
docker compose logs --tail 50 taskweb >&2
exit 1
REMOTE
