# CalDAV Task Manager

A self-hosted web interface for managing tasks stored on a [Radicale](https://radicale.org/) (or any CalDAV) server. Built because no decent web UI for CalDAV tasks existed.

## Features

- **Full VTODO CRUD** — create, edit, complete, delete tasks
- **Subtasks** — parent/child task relationships via `RELATED-TO`
- **Recurring tasks** — RRULE editor (daily, weekly, monthly, yearly with interval and end conditions)
- **Tags** — `CATEGORIES` field, filterable from sidebar
- **Virtual tags** — computed at runtime: `OVERDUE`, `DUE_TODAY`, `DUE_WEEK`, `STARRED`, `HIGH`, `PARENT`, `RECURRING`, and more
- **Smart filters** — sidebar links for common views with live badge counts
- **Bookmarkable URLs** — entire filter state lives in query params (`?status=pending&virtual=OVERDUE&tags=work`)
- **Saved views** — name and save any filter combination, stored in browser `localStorage`
- **Priority** — maps to iCalendar `PRIORITY` (1–4 high, 5 medium, 6–9 low)
- **Location** — Apple Reminders-compatible location triggers (`arriving:home`, `departing:work`, etc.)
- **Password auth** — single-password session login, 30-day cookie
- **Mobile-friendly** — responsive layout with slide-in sidebar drawer

## Quick Start (Docker)

```bash
git clone https://github.com/bbrendon/taskweb_caldav.git
cd taskweb_caldav

cp .env.example .env
# Edit .env — set your CalDAV credentials and APP_PASSWORD

docker compose up -d --build
```

Open `http://your-server:38000`.

To update after pulling new code:

```bash
docker compose up -d --build
```

## Configuration

All configuration is done via environment variables. Copy `.env.example` to `.env` and edit:

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_PASSWORD` | `changeme` | Login password |
| `SECRET_KEY` | insecure default | Django secret key — change in production |
| `DEBUG` | `false` | Enable Django debug mode |
| `ALLOWED_HOSTS` | `*` | Comma-separated allowed hostnames |
| `PORT` | `8080` | Host port to expose |
| `CALDAV_URL` | — | CalDAV server base URL |
| `CALDAV_USERNAME` | — | CalDAV username |
| `CALDAV_PASSWORD` | — | CalDAV password |
| `CALDAV_CALENDAR` | `Tasks` | Calendar/collection name |

## Local Development

**Requirements:** Python 3.12+, Node 20+

```bash
# Backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py runserver 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Or use the convenience script from the project root:

```bash
./start.sh
```

Frontend: `http://localhost:5173`
API: `http://localhost:8000/api/`

The Vite dev server proxies `/api/` to the Django backend, so no CORS configuration is needed during development.

## Stack

| Layer | Technology |
|-------|-----------|
| Backend | Django 5 + Django REST Framework |
| CalDAV | python-caldav + icalendar |
| Frontend | Vue 3 + Vite |
| State | Pinia |
| Routing | Vue Router 4 |
| UI | Naive UI |
| HTTP client | Axios |
| Production server | gunicorn + whitenoise |
| Deployment | Docker (single container) |

## Docs

- [Architecture](docs/architecture.md) — how it works, data flow, VTODO field mapping
- [API Reference](docs/api.md) — REST endpoints and query parameters
