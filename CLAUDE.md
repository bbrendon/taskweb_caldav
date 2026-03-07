# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Start both servers (recommended)
```bash
./start.sh
```

### Backend only
```bash
cd backend
source venv/bin/activate
python manage.py runserver 8000
```

### Frontend only
```bash
cd frontend
npm run dev        # dev server on :5173
npm run build      # production build
```

### Django checks
```bash
cd backend && source venv/bin/activate
python manage.py check
```

### Add a Python dependency
```bash
cd backend && source venv/bin/activate && pip install <pkg>
# Then update requirements.txt manually
```

## Architecture

This is a personal task manager that uses **CalDAV as the only data store** — there is no Django database (`DATABASES = {}`). All persistence goes through the Radicale server at `https://cd.brendon.net`.

### Request flow
```
Browser → Vite dev proxy (/api/*) → Django DRF → CalDAVService → Radicale server
```
In production, the browser hits Django directly. In dev, Vite proxies `/api` to `:8000`.

### Backend (`backend/`)

**`tasks/caldav_service.py`** — The core layer. `CalDAVService` wraps `python-caldav` and `icalendar` to perform all VTODO CRUD. A module-level singleton is returned by `get_service()` — it holds a live connection to the CalDAV server. All methods return plain Python dicts (not model instances).

**`tasks/virtual_tags.py`** — Pure functions that compute derived tags (OVERDUE, DUE_TODAY, STARRED, HIGH, PARENT, etc.) at request time from task field values. `add_virtual_tags(all_tasks)` mutates each dict to add a `virtual_tags` list. Must receive the full task list to detect PARENT relationships.

**`tasks/views.py`** — DRF `ViewSet` (not `ModelViewSet`). Filtering and sorting happen in Python after fetching all tasks from CalDAV (`_apply_filters`, `_apply_sort`). Virtual tags are always computed on the full list before filtering so PARENT detection is accurate.

**`tasks/serializers.py`** — `validate_task_input()` normalizes and validates incoming request data. Priority accepts both integers (0–9) and strings (`"high"`, `"medium"`, `"low"`).

### Frontend (`frontend/src/`)

**URL = filter state.** The entire filter/sort state lives in `?query` params. Components never store filter state locally — they read `route.query` and call `tasksStore.fetchTasks(route.query)`. `AppShell.vue` watches `route.query` (deep) and re-fetches on every change.

**`stores/tasks.js`** — Pinia store holding the fetched task list. Acts as a local cache; individual task mutations update the cache in place after the API call confirms success.

**`stores/ui.js`** — Tracks `activeTaskUid` (which task is open in `TaskDetail`), `showTaskForm` / `editingTask` (create vs. edit mode), and `savedViews` (persisted to `localStorage` under key `taskweb2_saved_views`).

**`api/tasks.js`** — Thin Axios wrapper. Base URL is `/api` (resolved via Vite proxy in dev). All methods return raw Axios promises.

### VTODO ↔ App field mapping (non-obvious ones)
| App field | VTODO property |
|-----------|---------------|
| `tags` | `CATEGORIES` |
| `starred` | `X-STARRED` (`TRUE`/`FALSE`) |
| `parent_uid` | `RELATED-TO;RELTYPE=PARENT` |
| `recurrence` | `RRULE` string (e.g. `FREQ=WEEKLY;INTERVAL=2`) |
| `priority` | `PRIORITY` int: 0=none, 1–4=high, 5=medium, 6–9=low |

### Priority encoding
`PRIORITY` in VTODO is an integer. The app uses: 0 = none, 1–4 = high, 5 = medium, 6–9 = low. This matches RFC 5545 conventions.

### CalDAV service singleton
`get_service()` reuses a single `CalDAVService` instance across all requests. If the CalDAV connection drops or the calendar is renamed, restart the Django process to re-initialize it.

### Location field
The `location` field maps to Apple Reminders geofence triggers. Recognized values: `arriving:home`, `departing:home`, `arriving:work`, `departing:work`, `arriving:car`, `departing:car`. `TaskForm.vue` offers these as autocomplete options.
