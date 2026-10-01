# TaskWeb

Single-user task manager PWA (iPhone home screen + desktop) on top of a Radicale
CalDAV server. The same calendar also syncs to iPhone Reminders.

## Layout

- `backend/` FastAPI app (`app/main.py`), single uvicorn worker: the task index lives in
  process memory (`app/store.py`). Auth: argon2 password hash + signed cookie (`app/auth.py`).
- `frontend/` Vue 3 + TS + Vite + Pinia PWA. Filtering/sorting is client-side
  (`src/lib/filters.ts`); `npm run build` writes into `backend/app/static/`.
- `../task-caldav-lib` (separate repo, branch `v0.2`) holds all CalDAV/VTODO logic:
  parsing, writes with ETag If-Match, recurrence, alarms. Installed editable into `.venv`.
- `config/taskweb.yaml` (gitignored; copy `taskweb.example.yaml`): timezone, tags, places.
- `scripts/`: `dev.sh`, `seed_dev.py`, `backup_calendar.py`, `migrate_repeats.py`, `purge_completed.py`.

## Commands

```bash
./scripts/dev.sh                                   # throwaway Radicale :5233 + API :8000 + Vite :5173, password taskweb-dev
.venv/bin/python -m pytest backend/tests -q        # from repo root (or cd backend)
(cd ../task-caldav-lib && .venv/bin/python -m pytest -q)
(cd frontend && npx vue-tsc --noEmit && npm run build)
./deploy.sh                                        # rsync to 10.2.2.222:/srv/taskweb_caldav, docker compose build/up on :38000
.venv/bin/python scripts/backup_calendar.py        # read-only backup of the real calendar to backups/
```

Tests start their own Radicale process; Docker is not installed on the laptop (only on the VM).

## Data rules (real calendar)

- Repeats: "after done" = `X-TASKWEB-RECUR-AFTER:P30D` (not RRULE) and completing rolls the
  same task forward; fixed schedules use RRULE. Reminders can't see after-done repeats, so the
  server rolls forward tasks Reminders marked COMPLETED (`reconcile_external_completions`).
- Never drop unknown properties (2Do metadata, Apple X- props): edits mutate the original component.
- Radicale truncates `X-APPLE-STRUCTURED-LOCATION` at an unescaped comma, so geo is written as
  `geo:lat\,lon`. iPhone accepts this (verified).
- All-day dates are `VALUE=DATE`; timed values are stored UTC and shown in the configured tz.
- Scripts that write to the real server preview by default and take a backup before `--apply`.
- Dev never touches the real server: `dev.sh` overrides every `CALDAV_*` variable.

## Deploy notes

Server-only state is never synced: `/srv/taskweb_caldav/.env` (secrets) and `data/` (saved
views). The session cookie is `Secure`, so log in via the HAProxy HTTPS hostname, not :38000.
`APP_PASSWORD_HASH` must stay single-quoted in `.env` (docker compose would expand `$`).
