import uuid
from datetime import date, datetime, timezone
from typing import Optional

import caldav
import niquests.auth
from dateutil import rrule as dateutil_rrule
from icalendar import Alarm, Calendar, Parameters, Todo, vDate, vDatetime, vRecur, vText

from app.config import settings
from app.models import Task, TaskCreate, TaskLocation, TaskUpdate


def get_client() -> caldav.DAVClient:
    return caldav.DAVClient(
        url=settings.CALDAV_URL,
        auth=niquests.auth.HTTPBasicAuth(settings.CALDAV_USERNAME, settings.CALDAV_PASSWORD),
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


def _parse_location_alarm(ical) -> Optional[TaskLocation]:
    """Walk VALARM subcomponents looking for Apple's proximity alarm.

    Handles two kinds:
    - Geo-fence (ARRIVE/DEPART): has X-APPLE-STRUCTURED-LOCATION with lat/lng.
    - CarPlay (CONNECT/DISCONNECT): no location, just the proximity value.
    """
    for sub in getattr(ical, "subcomponents", []):
        if sub.name != "VALARM":
            continue
        if "X-APPLE-PROXIMITY" not in sub:
            continue
        proximity = str(sub["X-APPLE-PROXIMITY"]).upper()

        # CarPlay connect/disconnect — no geo-fence, no structured location
        if proximity in ("CONNECT", "DISCONNECT"):
            title = "Getting In Car" if proximity == "CONNECT" else "Getting Out Of Car"
            return TaskLocation(title=title, proximity=proximity)

        loc_prop = sub.get("X-APPLE-STRUCTURED-LOCATION")
        if not loc_prop:
            continue
        val = str(loc_prop)
        lat, lng = None, None
        if val.startswith("geo:"):
            parts = val[4:].split(",")
            try:
                lat = float(parts[0])
                if len(parts) > 1:
                    lng = float(parts[1])
            except (ValueError, IndexError):
                pass
        params = getattr(loc_prop, "params", {})
        title = str(params.get("X-TITLE", "")).strip() or "Location"
        address = str(params.get("X-ADDRESS", "")).strip()
        return TaskLocation(title=title, address=address, lat=lat, lng=lng, proximity=proximity)
    return None


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

        location_alarm = _parse_location_alarm(ical)

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
            location_alarm=location_alarm,
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


def _build_location_alarm(loc: TaskLocation) -> Alarm:
    """Build an Apple-compatible proximity VALARM."""
    alarm = Alarm()
    alarm.add("ACTION", "DISPLAY")
    alarm.add("DESCRIPTION", "Reminder")
    alarm_uid = str(uuid.uuid4()).upper()
    alarm.add("UID", alarm_uid)

    # Apple's magic sentinel trigger date for proximity alarms
    trigger = vDatetime(datetime(1976, 4, 1, 0, 55, 45, tzinfo=timezone.utc))
    trigger.params = Parameters({"VALUE": "DATE-TIME"})
    alarm["TRIGGER"] = trigger

    alarm.add("X-APPLE-PROXIMITY", loc.proximity)

    # CarPlay triggers (CONNECT/DISCONNECT) have no geo-fence location
    if loc.proximity not in ("CONNECT", "DISCONNECT") and loc.lat is not None and loc.lng is not None:
        geo_val = vText(f"geo:{loc.lat},{loc.lng}")
        geo_val.params = Parameters({
            "VALUE": "URI",
            "X-ADDRESS": loc.address,
            "X-APPLE-RADIUS": "0",
            "X-APPLE-REFERENCEFRAME": "0",
            "X-TITLE": loc.title,
        })
        alarm["X-APPLE-STRUCTURED-LOCATION"] = geo_val

    alarm.add("X-WR-ALARMUID", alarm_uid)
    return alarm


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

    if task_data.location_alarm:
        todo.add_component(_build_location_alarm(task_data.location_alarm))

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


def _update_ical_inplace(existing_data: str, merged: TaskCreate) -> bytes:
    """Update only known fields in the existing VTODO, leaving everything else
    (X-APPLE-MAPKITHANDLE, etc.) untouched. Location VALARM is replaced if
    location_alarm is set, or stripped if it is None."""
    cal = Calendar.from_ical(existing_data)
    now = datetime.now(tz=timezone.utc)

    for component in cal.walk():
        if component.name != "VTODO":
            continue

        def _set(name, value):
            if name in component:
                del component[name]
            if value is not None:
                component.add(name, value)

        _set("SUMMARY", merged.title)
        _set("DESCRIPTION", merged.description)
        _set("DUE", merged.due)

        if "PRIORITY" in component:
            del component["PRIORITY"]
        component.add("PRIORITY", merged.priority if merged.priority is not None else 0)

        if "CATEGORIES" in component:
            del component["CATEGORIES"]
        if merged.tags:
            component.add("CATEGORIES", merged.tags)

        if "STATUS" in component:
            del component["STATUS"]
        component.add("STATUS", merged.status or "NEEDS-ACTION")

        if merged.status == "COMPLETED":
            if "COMPLETED" not in component:
                component.add("COMPLETED", now)
        else:
            if "COMPLETED" in component:
                del component["COMPLETED"]

        if "RRULE" in component:
            del component["RRULE"]
        if merged.recurrence:
            rrule_str = merged.recurrence
            if rrule_str.startswith("RRULE:"):
                rrule_str = rrule_str[6:]
            component.add("RRULE", vRecur.from_ical(rrule_str))

        # Strip existing Apple location VALARM, then add new one if provided
        component.subcomponents = [
            sc for sc in component.subcomponents
            if not (sc.name == "VALARM" and "X-APPLE-PROXIMITY" in sc)
        ]
        if merged.location_alarm:
            component.add_component(_build_location_alarm(merged.location_alarm))

        if "LAST-MODIFIED" in component:
            del component["LAST-MODIFIED"]
        component.add("LAST-MODIFIED", now)

        break

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
        location_alarm=task_data.location_alarm,
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
        location_alarm=task_data.location_alarm if "location_alarm" in provided else existing.location_alarm,
    )

    ical_bytes = _update_ical_inplace(existing_todo.data, merged)
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
        location_alarm=merged.location_alarm,
    )


def delete_todo(calendar, uid: str) -> bool:
    todo = _find_todo_by_uid(calendar, uid)
    if not todo:
        return False
    todo.delete()
    return True


def _next_occurrence(rrule_str: str, from_date: date) -> Optional[date]:
    """Return the next recurrence date strictly after from_date."""
    rule_str = rrule_str.removeprefix("RRULE:")
    try:
        dtstart = datetime(from_date.year, from_date.month, from_date.day)
        rule = dateutil_rrule.rrulestr(f"RRULE:{rule_str}", dtstart=dtstart)
        nxt = rule.after(dtstart)
        return nxt.date() if nxt else None
    except Exception as e:
        print(f"Error computing next recurrence: {e}")
        return None


def toggle_complete(calendar, uid: str) -> Optional[Task]:
    existing_todo = _find_todo_by_uid(calendar, uid)
    if not existing_todo:
        return None

    existing = parse_vtodo(existing_todo)
    if not existing:
        return None

    # For recurring tasks being marked complete: advance to next occurrence
    # instead of marking permanently completed.
    if existing.status != "COMPLETED" and existing.recurrence:
        from_date = existing.due or date.today()
        next_due = _next_occurrence(existing.recurrence, from_date)
        return update_todo(calendar, uid, TaskUpdate(status="NEEDS-ACTION", due=next_due))

    new_status = "NEEDS-ACTION" if existing.status == "COMPLETED" else "COMPLETED"
    return update_todo(calendar, uid, TaskUpdate(status=new_status))
