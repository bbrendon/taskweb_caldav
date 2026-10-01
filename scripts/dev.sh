#!/usr/bin/env bash
# Local development: throwaway Radicale with sample data + API (:8000) + Vite (:5173).
# Your real Radicale is never contacted: every CALDAV_* setting is overridden here.
# Dev login password: taskweb-dev
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEV="$ROOT/data/dev"
PY="$ROOT/.venv/bin/python"
mkdir -p "$DEV"

pids=()
cleanup() { kill "${pids[@]}" 2>/dev/null || true; }
trap cleanup EXIT INT TERM

"$PY" -m radicale --storage-filesystem-folder="$DEV/radicale" --auth-type=none \
  --server-hosts=127.0.0.1:5233 --logging-level=warning &
pids+=($!)
for _ in $(seq 50); do nc -z 127.0.0.1 5233 2>/dev/null && break; sleep 0.1; done

export CALDAV_URL=http://127.0.0.1:5233/ CALDAV_USERNAME=dev CALDAV_PASSWORD=dev CALDAV_CALENDAR=Tasks
export COOKIE_SECURE=false DATA_DIR="$DEV" SESSION_SECRET=dev-only-secret
export APP_PASSWORD_HASH="$("$PY" -c "from argon2 import PasswordHasher; print(PasswordHasher().hash('taskweb-dev'))")"

"$PY" "$ROOT/scripts/seed_dev.py"

(cd "$ROOT/backend" && exec "$PY" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload --reload-dir app --reload-dir ../../task-caldav-lib/task_caldav_lib) &
pids+=($!)
(cd "$ROOT/frontend" && exec npx vite --host 127.0.0.1 --port 5173 --strictPort) &
pids+=($!)
wait
