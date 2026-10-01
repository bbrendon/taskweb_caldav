"""Shared helpers for scripts that act on old completed tasks (purge, archive)."""
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dateutil.parser import isoparse
from task_caldav_lib import CalDAVService, Task

from backup_calendar import load_env

ROOT = Path(__file__).resolve().parent.parent


def connect() -> CalDAVService:
    """Service for the calendar in .env (exported CALDAV_* variables take precedence)."""
    load_env(ROOT / '.env')
    svc = CalDAVService(
        os.environ['CALDAV_URL'], os.environ['CALDAV_USERNAME'], os.environ['CALDAV_PASSWORD'],
        os.environ.get('CALDAV_CALENDAR', 'Tasks'), tz='America/Los_Angeles',
    )
    svc.refresh()
    return svc


def finished_at(t: Task) -> datetime | None:
    stamp = t.completed_at or t.last_modified
    if not stamp:
        return None
    dt = isoparse(stamp)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


@dataclass
class Selection:
    cutoff: datetime
    tasks: list[Task] = field(default_factory=list)          # oldest first
    pulled_in: list[Task] = field(default_factory=list)      # recent completed subtasks deleted with a parent
    skipped: list[Task] = field(default_factory=list)        # have open subtasks
    without_completed_date: int = 0

    @property
    def everything(self) -> list[Task]:
        return self.tasks + self.pulled_in


def select_old_completed(svc: CalDAVService, days: int) -> Selection:
    """Completed tasks finished more than `days` ago, plus completed subtasks that go with them.

    Never selects open tasks or "repeat after done" tasks. A task with any open
    descendant is skipped, since deleting it would orphan or delete open work.
    """
    sel = Selection(cutoff=datetime.now(timezone.utc) - timedelta(days=days))
    for t in svc.tasks():
        if t.status not in ('COMPLETED', 'CANCELLED') or t.recur_after:
            continue
        when = finished_at(t)
        if when is None or when >= sel.cutoff:
            continue
        if any(d.is_open for d in svc.descendants(t.uid)):
            sel.skipped.append(t)
            continue
        sel.without_completed_date += not t.completed_at
        sel.tasks.append(t)
    sel.tasks.sort(key=lambda t: finished_at(t))

    chosen = {t.uid for t in sel.tasks}
    for t in list(sel.tasks):
        for d in svc.descendants(t.uid):
            if d.uid not in chosen:
                chosen.add(d.uid)
                sel.pulled_in.append(d)
    return sel


def delete_selected(svc: CalDAVService, sel: Selection) -> tuple[set[str], list[str]]:
    """Delete the selection (children go with their parent). Returns (deleted uids, errors)."""
    deleted: set[str] = set()
    errors: list[str] = []
    for t in sel.tasks:
        if t.uid in deleted:
            continue
        try:
            deleted.update(svc.delete(t.uid, children='delete'))
        except Exception as e:
            errors.append(f'{t.title}: {e}')
    return deleted, errors
