# TaskWeb CalDAV — User Guide

A web interface for CalDAV task servers. Tasks are stored on your CalDAV server and synced in real time.

---

## Table of Contents

1. [Interface Overview](#interface-overview)
2. [Creating & Editing Tasks](#creating--editing-tasks)
3. [Task Fields](#task-fields)
4. [Quick Filters (Sidebar)](#quick-filters-sidebar)
5. [Smart Search](#smart-search)
6. [Saved Searches](#saved-searches)
7. [Location Alerts](#location-alerts)
8. [Mobile](#mobile)

---

## Interface Overview

The app has three main areas:

- **Sidebar (left)** — navigation, quick filters, tags, saved searches
- **Task list (center)** — sorted task rows
- **Modal** — create/edit form, opened as an overlay

### Task Row

Each row shows:

| Element | Description |
|---|---|
| Circle button (left) | Toggle complete — gray = incomplete, green = complete |
| Star button | Toggle favourite — hollow = not starred, yellow = starred |
| Title | Click to open edit form |
| Due date badge | Red = overdue, yellow = today, gray = future |
| Priority badge | Red = H, orange = M, gray = L |
| Recurrence icon | Circular arrows; hover to see the RRULE |
| Location badge | Green; click to open Google Maps |
| Tag badges | Blue; click a tag in the sidebar to filter by it |
| Edit / Delete (hover) | Appear on the right when hovering a row |

---

## Creating & Editing Tasks

- Click **New Task** (top of sidebar or top-right on mobile) to open the create form.
- Click any task title or the pencil icon to open the edit form.
- Press **Escape** or click outside the modal to cancel.

---

## Task Fields

| Field | Notes |
|---|---|
| **Title** | Required |
| **Description** | Free text, multi-line |
| **Due Date** | Date picker |
| **Priority** | None / High / Medium / Low |
| **Status** | Pending · In Progress · Completed · Cancelled |
| **Tags** | Comma-separated. The internal `fav` tag is hidden and managed by the star button. |
| **Recurrence** | Preset or custom RRULE (e.g. `FREQ=WEEKLY;BYDAY=MO,WE,FR`) |
| **Location Alert** | See [Location Alerts](#location-alerts) |

---

## Quick Filters (Sidebar)

| Filter | Shows |
|---|---|
| All Tasks | Pending + in-progress |
| Today | Due today |
| Overdue | Past due, not completed |
| This Week | Due within 7 days |
| Favorites | Starred tasks |
| Completed | Completed tasks |

Below the quick filters, **Tags** lists every tag in use. Click one to filter to tasks with that tag.

### Sorting

The task list header has three sort options: **Due** (default) · **Priority** · **Title**.

---

## Smart Search

The search box accepts a space- or comma-separated query. Tokens can be combined freely.

### Tag tokens

| Token | Effect |
|---|---|
| `+tag` | Must have this tag |
| `-tag` | Must not have this tag |
| `+single` | No recurrence |
| `+recurring` | Has recurrence |
| `-single` | Has recurrence (same as `+recurring`) |
| `-recurring` | No recurrence (same as `+single`) |

### Due tokens

| Token | Effect |
|---|---|
| `due:today` | Due today |
| `due:tomorrow` | Due tomorrow |
| `due:week` | Due within 7 days |
| `due:overdue` | Past due and not completed |
| `due:none` | No due date set |

### Status tokens

| Token | Effect |
|---|---|
| `status:pending` | Needs action or in progress |
| `status:completed` | Completed |
| `status:cancelled` | Cancelled |

### Priority tokens

| Token | Effect |
|---|---|
| `priority:H` | High |
| `priority:M` | Medium |
| `priority:L` | Low |

### Bare text

Any word that isn't a recognised token is treated as a text search across **title and description** (case-insensitive, AND logic).

### Examples

```
+work due:today
```
Work-tagged tasks due today.

```
+single status:pending
```
Non-recurring pending tasks (commas also work: `+single,status:pending`).

```
priority:H meeting
```
High-priority tasks with "meeting" in the title or description.

```
-recurring due:week
```
Non-recurring tasks due within 7 days.

```
+home +errands -shopping
```
Tasks tagged both "home" and "errands" but not "shopping".

---

## Saved Searches

1. Type a search query — a **bookmark icon** appears in the search box.
2. Click it to open the save panel.
3. Enter a name and click **Save**.

Saved searches appear in the sidebar. Click one to re-run it. Hover to reveal a delete button.

---

## Location Alerts

Location alerts trigger when you arrive at or depart from a place. They are stored as Apple-compatible geofence alarms on the task and sync to Apple Reminders / any Apple CalDAV client.

### Setting a location

1. In the task form, find the **Location Alert** section.
2. Either:
   - Click a **preset button** (pre-configured locations from `LOCATION_PRESETS`), or
   - Type in the search box and pick a result from the dropdown.
3. Once selected, a green badge shows the location name and proximity direction.
4. Toggle **Arriving / Departing** to choose which direction triggers the alert.
5. Click **×** to remove the location.

### Display

- Tasks with a location show a green badge in the task row.
- Click the badge to open Google Maps at those coordinates.

---

## Mobile

On small screens the sidebar is hidden by default.

- Tap the **hamburger menu** (top-left) to open the sidebar.
- Tap the backdrop or any sidebar link to close it.
- A **New Task** button appears top-right when the sidebar is hidden.
