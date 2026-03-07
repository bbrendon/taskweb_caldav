# Architecture

## Overview

The app is a thin web layer over a CalDAV server. There is no local database — the CalDAV server is the only data store. Django reads and writes VTODOs via the `python-caldav` library, computes derived state (virtual tags) in Python, and exposes a REST API. Vue consumes the API and keeps task state in a Pinia store.

```
Browser
  │
  ▼
gunicorn (port 8080)
  ├── /* → whitenoise serves Vue SPA (dist/)
  └── /api/* → Django REST Framework
                   └── CalDAVService → Radicale server
```

In development, Vite's dev server proxies `/api/` to Django on port 8000. In production, gunicorn handles everything directly.

## Request Flow

1. Browser loads `index.html` (served by whitenoise)
2. Vue Router runs a `beforeEach` guard that calls `GET /api/auth/check/`
3. If not authenticated, redirect to `/login`
4. On login, `POST /api/auth/login/` sets a signed-cookie session (30-day lifetime)
5. Task data is fetched from `GET /api/tasks/` with filter query params
6. Django fetches all VTODOs from CalDAV, computes virtual tags on the full set, applies filters in Python, and returns JSON
7. Vue caches the task list in Pinia; filter changes re-fetch from the API

## Backend

### `tasks/caldav_service.py`

`CalDAVService` wraps python-caldav. A module-level `get_service()` singleton avoids reconnecting on every request.

Key methods:
- `get_all_tasks(include_completed)` — fetches all VTODOs, parses with `icalendar.Calendar.from_ical(todo.data)`, returns list of dicts
- `get_task(uid)` — fetches a single VTODO by UID
- `create_task(data)` — builds a VCALENDAR/VTODO from a dict, PUTs to CalDAV
- `update_task(uid, data)` — fetches existing VTODO, merges fields, saves
- `delete_task(uid)` — deletes VTODO from server
- `complete_task(uid)` — sets STATUS=COMPLETED, COMPLETED=now

### `tasks/virtual_tags.py`

Pure functions with no I/O. `add_virtual_tags(all_tasks)` is called on the full task list before any filtering so that PARENT detection works correctly (a task is a PARENT if any other task has a `RELATED-TO` pointing to its UID).

### `tasks/auth_middleware.py`

`RequireAuthMiddleware` checks `request.session['authenticated']` for every `/api/` request except `/api/auth/login/` and `/api/auth/logout/`. Returns 401 JSON if not authenticated.

Sessions use Django's signed-cookie backend — no database needed.

## VTODO Field Mapping

| App field | VTODO property | Notes |
|-----------|---------------|-------|
| `uid` | `UID` | |
| `title` | `SUMMARY` | Required |
| `description` | `DESCRIPTION` | |
| `status` | `STATUS` | NEEDS-ACTION, IN-PROCESS, COMPLETED, CANCELLED |
| `priority` | `PRIORITY` | 0=none, 1–4=high, 5=medium, 6–9=low |
| `due` | `DUE` | ISO 8601 datetime |
| `start` | `DTSTART` | |
| `tags` | `CATEGORIES` | List of strings |
| `location` | `LOCATION` | Free text; Apple Reminders parses `arriving:home` etc. |
| `parent_uid` | `RELATED-TO;RELTYPE=PARENT` | |
| `recurrence` | `RRULE` | e.g. `FREQ=WEEKLY;INTERVAL=2` |
| `starred` | `X-STARRED` | Custom property: `TRUE` / `FALSE` |
| `completed_at` | `COMPLETED` | Set when marking complete |
| `percent` | `PERCENT-COMPLETE` | 0–100 |

## Virtual Tags

Computed at runtime in `virtual_tags.py` — never stored.

| Tag | Condition |
|-----|-----------|
| `OVERDUE` | `DUE` < now AND status ≠ COMPLETED/CANCELLED |
| `DUE_TODAY` | `DUE` date == today |
| `DUE_WEEK` | `DUE` date within next 7 days |
| `RECURRING` | has `RRULE` |
| `SINGLE` | no `RRULE` |
| `PARENT` | another task has `RELATED-TO` pointing to this UID |
| `CHILD` | has `RELATED-TO` with `RELTYPE=PARENT` |
| `STARRED` | `X-STARRED == TRUE` |
| `PENDING` | STATUS in NEEDS-ACTION or IN-PROCESS |
| `HIGH` | PRIORITY 1–4 |
| `MEDIUM` | PRIORITY 5 |
| `LOW` | PRIORITY 6–9 |
| `TAGGED` | has CATEGORIES |
| `UNTAGGED` | no CATEGORIES |

## Frontend

### URL as state

The entire filter state lives in URL query params:

```
/tasks?status=pending&virtual=OVERDUE,STARRED&tags=work&sort=-due&search=bug
```

Vue Router watches `route.query` and re-fetches tasks when it changes. This makes every filter view bookmarkable and shareable by copying the URL. Named saved views are just labelled copies of URL query strings stored in `localStorage`.

### Stores

- **`stores/tasks.js`** — task list, tags, virtual tag counts, all CRUD actions
- **`stores/ui.js`** — active task UID, form state, saved views

### Components

```
AppShell.vue       Layout: sidebar + main area
├── Sidebar.vue    Nav links, smart filters, tags, saved views, logout
├── SearchBar.vue  Text search, filter chips, "Save view" button
├── TaskList.vue   Filtered task list with subtask expansion
│   └── TaskRow.vue   Single row: checkbox, star, title, due, priority, tags
├── TaskDetail.vue Right panel: full task view with edit/complete/delete
└── TaskForm.vue   Create/edit modal: all fields including recurrence
    └── RecurrenceField.vue  RRULE builder UI
```

## Docker Build

The `Dockerfile` at the project root is a two-stage build:

1. **Node stage** — `npm ci && npm run build` produces `dist/`
2. **Python stage** — copies `backend/` and `dist/` (as `spa/`) into a single image, runs gunicorn

Whitenoise serves `spa/` at the root URL (`/`, `/assets/...`). A Django catch-all URL pattern serves `spa/index.html` for any path that isn't `/api/`, enabling Vue Router's HTML5 history mode.
