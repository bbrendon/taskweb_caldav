# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the app

```bash
source venv/bin/activate && python run.py
# → http://localhost:38000
```

Uvicorn runs with `reload=True`, so file changes are picked up automatically.

## Key architecture decisions

### Shared Jinja2 template instance
`app/templates_env.py` exports a single `templates` object with a `today` global (a `date`) that is refreshed on every request by `AuthMiddleware` in `app/main.py`. All routes **must** import `templates` from `templates_env`, never create their own `Jinja2Templates` instance.

### Middleware order matters
`app/main.py` adds two middlewares via `add_middleware()` (LIFO — last added = outermost):
1. `app.add_middleware(AuthMiddleware)` — reads `request.session`, added first → inner
2. `app.add_middleware(SessionMiddleware, ...)` — populates `request.session`, added second → outer (runs first on request path)

`SessionMiddleware` must always be added **after** `AuthMiddleware` so the session is populated before the auth check runs.

### Auth (two mechanisms, one middleware)
- **Option B** — login form at `/login` sets `session["authenticated"] = True`
- **Option C** — `?token=<AUTH_TOKEN>` query param or `X-Auth-Token` header; a valid token also sets the session so the token is only needed once per browser
- HTMX requests that fail auth get a `204 + HX-Redirect: /login` header instead of a 302 so HTMX does a full-page redirect rather than swapping a fragment

### CalDAV update merging — `model_fields_set`
`caldav_client.update_todo()` uses Pydantic's `model_fields_set` to distinguish "field explicitly set to None (user cleared it)" from "field not provided (partial update)". Callers like `toggle_complete(TaskUpdate(status=...))` only set one field and correctly fall back to existing values for all others. Full form edits always pass every field explicitly, allowing any field (including `due`) to be cleared.

### HTMX partial swap targets
- Task row updates (complete, favourite, edit): swap `outerHTML` of `#task-{uid}`
- Full list reload (filters, sort): swap `#task-list` innerHTML
- New task creation: `afterbegin` into `#tasks-container`
- Edit/new form: loaded into `#modal-content`; modal open/close is handled by `openModal()` / `closeModal()` in `static/app.js`

### "fav" tag is internal
Favouriting is stored as a `"fav"` CATEGORIES entry in the VTODO. The task row has a star button that posts to `/tasks/{uid}/favorite`. The edit form **filters `"fav"` out** of the visible tags field and uses a hidden `is_favorite` input to preserve it across saves — the PATCH route re-injects the tag if needed.

## Environment variables (`.env`)

| Variable | Purpose |
|---|---|
| `CALDAV_URL` | CalDAV server base URL |
| `CALDAV_USERNAME` / `CALDAV_PASSWORD` | CalDAV credentials |
| `CALDAV_CALENDAR_NAME` | Calendar to use (default: `Tasks`) |
| `SESSION_SECRET` | Signs the session cookie — keep random and secret |
| `AUTH_PASSWORD` | Login form password |
| `AUTH_TOKEN` | Static token for `?token=` / `X-Auth-Token` access |

Copy `.env.example` to `.env` to get started.

## Smart search syntax

Handled in `app/routes/search.py`. Tokens are space-separated:
- `+tag` / `-tag` — include / exclude tag
- `due:today` / `due:overdue` / `due:tomorrow` / `due:week` / `due:none`
- `status:pending` / `status:completed` / `status:cancelled`
- `priority:H` / `priority:M` / `priority:L`
- Bare words — case-insensitive AND search across title + description
