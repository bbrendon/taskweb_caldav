import uuid
from datetime import date, datetime, timezone
from typing import Optional

import caldav
from icalendar import Calendar, Todo, vText, vDate, vDatetime, vRecur

from app.config import settings
from app.models import Task, TaskCreate, TaskUpdate


def get_client() -> caldav.DAVClient:
    return caldav.DAVClient(
        url=settings.CALDAV_URL,
        username=settings.CALDAV_USERNAME,
        password=settings.CALDAV_PASSWORD,
    )


def get_calendar(client: Optional[caldav.DAVClient] = None):
    if client is None:
        client = get_client()
    principal = client.principal()
    calendars = principal.calendars()
    for cal in calendars:
        props = cal.get_properties([caldav.dav.DisplayName()])
        name = props.get("{DAV:}displayname", "")
        if name == settings.CALDAV_CALENDAR_NAME:
            return cal
    # Fallback: return first calendar that supports VTODO
    for cal in calendars:
        try:
            cal.todos()
            return cal
        except Exception:
            continue
    return calendars[0] if calendars else None


def parse_vtodo(todo_obj) -> Optional[Task]:
    try:
        ical = todo_obj.icalendar_component
        uid = str(ical.get("UID", ""))
        title = str(ical.get("SUMMARY", ""))
        if not uid or not title:
            return None

        description = None
        if ical.get("DESCRIPTION"):
            description = str(ical["DESCRIPTION"])

        due = None
        if ical.get("DUE"):
            due_val = ical["DUE"].dt
            if isinstance(due_val, datetime):
                due = due_val.date()
            elif isinstance(due_val, date):
                due = due_val

        priority = int(ical.get("PRIORITY", 0))

        tags = []
        if ical.get("CATEGORIES"):
            cats = ical["CATEGORIES"]
            if hasattr(cats, "cats"):
                tags = [str(c) for c in cats.cats]
            elif isinstance(cats, list):
                for cat in cats:
                    if hasattr(cat, "cats"):
                        tags.extend([str(c) for c in cat.cats])
                    else:
                        tags.append(str(cat))
            else:
                raw = str(cats)
                tags = [t.strip() for t in raw.split(",") if t.strip()]

        status = str(ical.get("STATUS", "NEEDS-ACTION"))

        recurrence = None
        if ical.get("RRULE"):
            rrule = ical["RRULE"]
            if isinstance(rrule, vRecur):
                recurrence = rrule.to_ical().decode("utf-8")
            else:
                recurrence = str(rrule)

        completed = None
        if ical.get("COMPLETED"):
            comp_val = ical["COMPLETED"].dt
            if isinstance(comp_val, datetime):
                completed = comp_val
            elif isinstance(comp_val, date):
                completed = datetime(comp_val.year, comp_val.month, comp_val.day, tzinfo=timezone.utc)

        return Task(
            uid=uid,
            title=title,
            description=description,
            due=due,
            priority=priority,
            tags=tags,
            status=status,
            recurrence=recurrence,
            completed=completed,
        )
    except Exception as e:
        print(f"Error parsing VTODO: {e}")
        return None


def get_todos(calendar) -> list[Task]:
    tasks = []
    try:
        todos = calendar.todos(include_completed=True)
        for todo in todos:
            task = parse_vtodo(todo)
            if task:
                tasks.append(task)
    except Exception as e:
        print(f"Error fetching todos: {e}")
    return tasks


def _build_ical(task_data: TaskCreate | TaskUpdate, uid: str) -> bytes:
    cal = Calendar()
    cal.add("PRODID", "-//TaskWeb CalDAV//EN")
    cal.add("VERSION", "2.0")

    todo = Todo()
    todo.add("UID", uid)

    if isinstance(task_data, TaskCreate):
        todo.add("SUMMARY", task_data.title)
    elif task_data.title:
        todo.add("SUMMARY", task_data.title)

    if task_data.description:
        todo.add("DESCRIPTION", task_data.description)

    if task_data.due:
        todo.add("DUE", task_data.due)

    priority = task_data.priority if task_data.priority is not None else 0
    todo.add("PRIORITY", priority)

    if task_data.tags:
        todo.add("CATEGORIES", task_data.tags)

    status = task_data.status or "NEEDS-ACTION"
    todo.add("STATUS", status)

    if task_data.recurrence:
        rrule_str = task_data.recurrence
        if rrule_str.startswith("RRULE:"):
            rrule_str = rrule_str[6:]
        todo.add("RRULE", vRecur.from_ical(rrule_str))

    now = datetime.now(tz=timezone.utc)
    todo.add("DTSTAMP", now)
    todo.add("CREATED", now)
    todo.add("LAST-MODIFIED", now)

    if status == "COMPLETED":
        todo.add("COMPLETED", now)

    cal.add_component(todo)
    return cal.to_ical()


def create_todo(calendar, task_data: TaskCreate) -> Task:
    uid = str(uuid.uuid4())
    ical_bytes = _build_ical(task_data, uid)
    calendar.save_todo(ical_bytes.decode("utf-8"))
    # Fetch back the created task
    todos = calendar.todos(include_completed=True)
    for todo in todos:
        t = parse_vtodo(todo)
        if t and t.uid == uid:
            return t
    # Return a task from task_data if fetch fails
    return Task(
        uid=uid,
        title=task_data.title,
        description=task_data.description,
        due=task_data.due,
        priority=task_data.priority,
        tags=task_data.tags,
        status=task_data.status,
        recurrence=task_data.recurrence,
    )


def _find_todo_by_uid(calendar, uid: str):
    try:
        todos = calendar.todos(include_completed=True)
        for todo in todos:
            ical = todo.icalendar_component
            if str(ical.get("UID", "")) == uid:
                return todo
    except Exception as e:
        print(f"Error finding todo by UID: {e}")
    return None


def update_todo(calendar, uid: str, task_data: TaskUpdate) -> Optional[Task]:
    existing_todo = _find_todo_by_uid(calendar, uid)
    if not existing_todo:
        return None

    existing = parse_vtodo(existing_todo)
    if not existing:
        return None

    # Use model_fields_set to distinguish "explicitly set to None" from "not provided".
    # This allows callers like toggle_complete (TaskUpdate(status=...)) to do partial
    # updates without clobbering other fields, while a full form edit can clear fields
    # by explicitly passing None/empty values.
    provided = task_data.model_fields_set
    merged = TaskCreate(
        title=task_data.title if "title" in provided else existing.title,
        description=task_data.description if "description" in provided else existing.description,
        due=task_data.due if "due" in provided else existing.due,
        priority=task_data.priority if "priority" in provided else existing.priority,
        tags=(task_data.tags if "tags" in provided else existing.tags) or [],
        status=task_data.status if "status" in provided else existing.status,
        recurrence=task_data.recurrence if "recurrence" in provided else existing.recurrence,
    )

    ical_bytes = _build_ical(merged, uid)
    existing_todo.data = ical_bytes.decode("utf-8")
    existing_todo.save()

    return Task(
        uid=uid,
        title=merged.title,
        description=merged.description,
        due=merged.due,
        priority=merged.priority,
        tags=merged.tags,
        status=merged.status,
        recurrence=merged.recurrence,
    )


def delete_todo(calendar, uid: str) -> bool:
    todo = _find_todo_by_uid(calendar, uid)
    if not todo:
        return False
    todo.delete()
    return True


def toggle_complete(calendar, uid: str) -> Optional[Task]:
    existing_todo = _find_todo_by_uid(calendar, uid)
    if not existing_todo:
        return None

    existing = parse_vtodo(existing_todo)
    if not existing:
        return None

    new_status = "NEEDS-ACTION" if existing.status == "COMPLETED" else "COMPLETED"
    return update_todo(calendar, uid, TaskUpdate(status=new_status))
