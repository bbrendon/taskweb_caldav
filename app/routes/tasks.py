from datetime import date
from typing import Optional

from fastapi import APIRouter, Form, Request, Response
from fastapi.responses import HTMLResponse

from app import caldav_client
from app.models import Task, TaskCreate, TaskUpdate, PRIORITY_VALUE
from app.templates_env import templates

router = APIRouter()


def _get_calendar():
    client = caldav_client.get_client()
    return caldav_client.get_calendar(client)


def _apply_filters(tasks: list[Task], status: str = None, priority: str = None,
                   tag: str = None, due_filter: str = None) -> list[Task]:
    today = date.today()
    result = tasks

    if status:
        if status == "pending":
            result = [t for t in result if t.status in ("NEEDS-ACTION", "IN-PROCESS")]
        elif status == "completed":
            result = [t for t in result if t.status == "COMPLETED"]
        elif status == "cancelled":
            result = [t for t in result if t.status == "CANCELLED"]

    if priority:
        pval = PRIORITY_VALUE.get(priority.upper())
        if pval is not None:
            result = [t for t in result if t.priority == pval]

    if tag:
        result = [t for t in result if tag in t.tags]

    if due_filter:
        from datetime import timedelta
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

    return result


def _sort_tasks(tasks: list[Task], sort_by: str = "due") -> list[Task]:
    if sort_by == "priority":
        def priority_key(t):
            p = t.priority if t.priority > 0 else 99
            return p
        return sorted(tasks, key=priority_key)
    elif sort_by == "title":
        return sorted(tasks, key=lambda t: t.title.lower())
    else:  # due (default)
        def due_key(t):
            if t.due is None:
                return date(9999, 12, 31)
            return t.due
        return sorted(tasks, key=due_key)


def _all_tags(tasks: list[Task]) -> list[str]:
    tags = set()
    for t in tasks:
        tags.update(t.tags)
    return sorted(tags)


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    cal = _get_calendar()
    tasks = caldav_client.get_todos(cal)
    pending = [t for t in tasks if t.status not in ("COMPLETED", "CANCELLED")]
    pending = _sort_tasks(pending)
    all_tags = _all_tags(tasks)
    return templates.TemplateResponse("index.html", {
        "request": request,
        "tasks": pending,
        "all_tags": all_tags,
        "active_filter": "all",
    })


@router.get("/tasks", response_class=HTMLResponse)
async def get_tasks(
    request: Request,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    tag: Optional[str] = None,
    due_filter: Optional[str] = None,
    sort: Optional[str] = "due",
    show_completed: Optional[bool] = False,
):
    cal = _get_calendar()
    all_tasks = caldav_client.get_todos(cal)

    if not show_completed and not status:
        tasks = [t for t in all_tasks if t.status not in ("COMPLETED", "CANCELLED")]
    else:
        tasks = all_tasks

    tasks = _apply_filters(tasks, status=status, priority=priority, tag=tag, due_filter=due_filter)
    tasks = _sort_tasks(tasks, sort_by=sort or "due")
    all_tags = _all_tags(all_tasks)

    return templates.TemplateResponse("partials/task_list.html", {
        "request": request,
        "tasks": tasks,
        "all_tags": all_tags,
        "sort": sort,
    })


@router.get("/tasks/new", response_class=HTMLResponse)
async def new_task_form(request: Request):
    return templates.TemplateResponse("partials/task_form.html", {
        "request": request,
        "task": None,
    })


@router.get("/tasks/{uid}/form", response_class=HTMLResponse)
async def edit_task_form(uid: str, request: Request):
    cal = _get_calendar()
    tasks = caldav_client.get_todos(cal)
    task = next((t for t in tasks if t.uid == uid), None)
    return templates.TemplateResponse("partials/task_form.html", {
        "request": request,
        "task": task,
    })


@router.post("/tasks", response_class=HTMLResponse)
async def create_task(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    due: Optional[str] = Form(None),
    priority: str = Form("0"),
    tags: str = Form(""),
    status: str = Form("NEEDS-ACTION"),
    recurrence: str = Form(""),
):
    due_date = None
    if due:
        try:
            due_date = date.fromisoformat(due)
        except ValueError:
            pass

    tag_list = [t.strip() for t in tags.split(",") if t.strip()]

    rrule = None
    if recurrence and recurrence != "none":
        rrule = recurrence

    task_data = TaskCreate(
        title=title,
        description=description or None,
        due=due_date,
        priority=int(priority),
        tags=tag_list,
        status=status,
        recurrence=rrule,
    )

    cal = _get_calendar()
    task = caldav_client.create_todo(cal, task_data)

    return templates.TemplateResponse("partials/task_row.html", {
        "request": request,
        "task": task,
    })


@router.patch("/tasks/{uid}", response_class=HTMLResponse)
async def update_task(
    uid: str,
    request: Request,
    title: str = Form(None),
    description: str = Form(None),
    due: Optional[str] = Form(None),
    priority: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    status: Optional[str] = Form(None),
    recurrence: Optional[str] = Form(None),
    is_favorite: str = Form("0"),
):
    due_date = None
    if due:
        try:
            due_date = date.fromisoformat(due)
        except ValueError:
            pass

    tag_list = [t.strip() for t in (tags or "").split(",") if t.strip()]
    # Re-inject the internal "fav" tag if the task was a favourite;
    # the edit form hides it from the visible tags field to avoid confusion.
    if is_favorite == "1" and "fav" not in tag_list:
        tag_list.append("fav")

    rrule = None
    if recurrence is not None:
        rrule = recurrence if recurrence and recurrence != "none" else None

    task_data = TaskUpdate(
        title=title,
        description=description,
        due=due_date,
        priority=int(priority) if priority else None,
        tags=tag_list,
        status=status,
        recurrence=rrule,
    )

    cal = _get_calendar()
    task = caldav_client.update_todo(cal, uid, task_data)

    if not task:
        return Response(status_code=404)

    return templates.TemplateResponse("partials/task_row.html", {
        "request": request,
        "task": task,
    })


@router.delete("/tasks/{uid}", response_class=HTMLResponse)
async def delete_task(uid: str):
    cal = _get_calendar()
    caldav_client.delete_todo(cal, uid)
    return HTMLResponse("")


@router.post("/tasks/{uid}/complete", response_class=HTMLResponse)
async def toggle_complete(uid: str, request: Request):
    cal = _get_calendar()
    task = caldav_client.toggle_complete(cal, uid)
    if not task:
        return Response(status_code=404)
    return templates.TemplateResponse("partials/task_row.html", {
        "request": request,
        "task": task,
    })


@router.post("/tasks/{uid}/favorite", response_class=HTMLResponse)
async def toggle_favorite(uid: str, request: Request):
    cal = _get_calendar()
    all_tasks = caldav_client.get_todos(cal)
    task = next((t for t in all_tasks if t.uid == uid), None)
    if not task:
        return Response(status_code=404)
    tags = task.tags.copy()
    if "fav" in tags:
        tags.remove("fav")
    else:
        tags.append("fav")
    updated = caldav_client.update_todo(cal, uid, TaskUpdate(tags=tags))
    if not updated:
        return Response(status_code=500)
    return templates.TemplateResponse("partials/task_row.html", {
        "request": request,
        "task": updated,
    })
