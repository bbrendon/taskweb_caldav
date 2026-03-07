# API Reference

Base URL: `/api/`

All endpoints require an authenticated session cookie. Call `POST /api/auth/login/` first.

## Auth

### `POST /api/auth/login/`

```json
{ "password": "yourpassword" }
```

Sets a signed-cookie session on success. Returns `200` with `{ "ok": true }` or `401` on wrong password.

### `POST /api/auth/logout/`

Clears the session. Returns `200`.

### `GET /api/auth/check/`

Returns `{ "authenticated": true/false }`. Used by the frontend router guard.

---

## Tasks

### `GET /api/tasks/`

List tasks. All query params are optional and can be combined.

| Param | Example | Description |
|-------|---------|-------------|
| `status` | `pending` | Filter by status: `pending`, `completed`, `cancelled` |
| `tags` | `work,home` | Comma-separated tags — task must have **all** listed tags |
| `virtual` | `OVERDUE,STARRED` | Comma-separated virtual tags — task must have **all** listed |
| `priority` | `high` | Priority band: `high`, `medium`, `low`, `none` |
| `search` | `dentist` | Full-text search in title and description |
| `parent_uid` | `abc-123` | Return only children of the given task UID |
| `sort` | `-due` | Sort field; prefix `-` for descending. Options: `due`, `priority`, `title` |

**Response:**
```json
{
  "tasks": [ ...task objects... ],
  "total": 42
}
```

### `POST /api/tasks/`

Create a task. `title` is required.

**Request body:**
```json
{
  "title": "Buy milk",
  "description": "Whole milk, 2L",
  "due": "2024-12-01T18:00:00Z",
  "start": "2024-11-30T00:00:00Z",
  "priority": "high",
  "tags": ["shopping", "home"],
  "location": "arriving:home",
  "starred": false,
  "recurrence": "FREQ=WEEKLY;INTERVAL=1",
  "parent_uid": "parent-task-uid-here"
}
```

`priority` accepts either a string (`"high"`, `"medium"`, `"low"`, `"none"`) or an integer (0–9).

**Response:** Full task object, `201 Created`.

### `GET /api/tasks/{uid}/`

Get a single task by UID. Returns full task object including `virtual_tags`.

### `PUT /api/tasks/{uid}/`

Full update. Same body as POST (all fields replaced).

### `PATCH /api/tasks/{uid}/`

Partial update. Only send the fields you want to change.

### `DELETE /api/tasks/{uid}/`

Delete a task. Returns `204 No Content`.

### `POST /api/tasks/{uid}/complete/`

Mark a task as completed. Sets `STATUS=COMPLETED` and `COMPLETED=<now>`. Returns updated task object.

---

## Tags

### `GET /api/tags/`

Returns all unique tag strings across all tasks.

```json
{ "tags": ["home", "shopping", "work"] }
```

### `GET /api/virtual-tags/`

Returns counts of each virtual tag across all non-completed tasks.

```json
{
  "virtual_tags": {
    "OVERDUE": 3,
    "DUE_TODAY": 1,
    "STARRED": 7,
    "HIGH": 2
  }
}
```

---

## Task Object

```json
{
  "uid": "abc-123-def-456",
  "title": "Buy milk",
  "description": "Whole milk, 2L",
  "status": "NEEDS-ACTION",
  "priority": 1,
  "due": "2024-12-01T18:00:00+00:00",
  "start": null,
  "tags": ["shopping", "home"],
  "location": "arriving:home",
  "starred": false,
  "recurrence": "FREQ=WEEKLY;INTERVAL=1",
  "parent_uid": null,
  "completed_at": null,
  "percent": 0,
  "virtual_tags": ["PENDING", "OVERDUE", "HIGH", "TAGGED", "SINGLE"]
}
```

`status` values: `NEEDS-ACTION`, `IN-PROCESS`, `COMPLETED`, `CANCELLED`

`priority` integer: `0`=none, `1`–`4`=high, `5`=medium, `6`–`9`=low
