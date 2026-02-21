from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app import caldav_client
from app.models import Task, PRIORITY_VALUE
from app.templates_env import templates

router = APIRouter()


def parse_search_query(q: str) -> dict:
    """Parse taskwarrior-inspired search query into filter components."""
    tokens = q.strip().split()
    filters = {
        "include_tags": [],
        "exclude_tags": [],
        "due": None,
        "status": None,
        "priority": None,
        "text": [],
    }

    for token in tokens:
        if token.startswith("+"):
            filters["include_tags"].append(token[1:])
        elif token.startswith("-") and len(token) > 1:
            filters["exclude_tags"].append(token[1:])
        elif token.startswith("due:"):
            filters["due"] = token[4:]
        elif token.startswith("status:"):
            filters["status"] = token[7:]
        elif token.startswith("priority:"):
            filters["priority"] = token[9:]
        else:
            filters["text"].append(token)

    return filters


def apply_search_filters(tasks: list[Task], filters: dict) -> list[Task]:
    today = date.today()
    result = tasks

    # Include tags
    for tag in filters["include_tags"]:
        result = [t for t in result if tag in t.tags]

    # Exclude tags
    for tag in filters["exclude_tags"]:
        result = [t for t in result if tag not in t.tags]

    # Due filter
    due_filter = filters["due"]
    if due_filter == "today":
        result = [t for t in result if t.due == today]
    elif due_filter == "overdue":
        result = [t for t in result if t.due and t.due < today and not t.is_completed]
    elif due_filter == "tomorrow":
        tomorrow = today + timedelta(days=1)
        result = [t for t in result if t.due == tomorrow]
    elif due_filter == "week":
        week_end = today + timedelta(days=7)
        result = [t for t in result if t.due and today <= t.due <= week_end]
    elif due_filter == "none":
        result = [t for t in result if t.due is None]

    # Status filter
    status = filters["status"]
    if status == "pending":
        result = [t for t in result if t.status in ("NEEDS-ACTION", "IN-PROCESS")]
    elif status == "completed":
        result = [t for t in result if t.status == "COMPLETED"]
    elif status == "cancelled":
        result = [t for t in result if t.status == "CANCELLED"]

    # Priority filter
    priority = filters["priority"]
    if priority:
        if priority.upper() in PRIORITY_VALUE:
            pval = PRIORITY_VALUE[priority.upper()]
            result = [t for t in result if t.priority == pval]

    # Text search (case-insensitive, AND logic across terms)
    for term in filters["text"]:
        term_lower = term.lower()
        result = [
            t for t in result
            if term_lower in t.title.lower()
            or (t.description and term_lower in t.description.lower())
        ]

    return result


@router.get("/search", response_class=HTMLResponse)
async def search(request: Request, q: Optional[str] = ""):
    client = caldav_client.get_client()
    cal = caldav_client.get_calendar(client)
    all_tasks = caldav_client.get_todos(cal)

    if not q or not q.strip():
        # Empty search: show pending tasks
        tasks = [t for t in all_tasks if t.status not in ("COMPLETED", "CANCELLED")]
    else:
        filters = parse_search_query(q)
        # If no status filter specified, include all tasks for search
        tasks = apply_search_filters(all_tasks, filters)

    # Sort by due date
    def due_key(t):
        if t.due is None:
            return date(9999, 12, 31)
        return t.due

    tasks = sorted(tasks, key=due_key)
    all_tags = sorted({tag for t in all_tasks for tag in t.tags})

    return templates.TemplateResponse("partials/task_list.html", {
        "request": request,
        "tasks": tasks,
        "all_tags": all_tags,
        "sort": "due",
        "search_query": q,
    })
