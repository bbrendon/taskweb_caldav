"""
Process-wide task store: one CalDAVService behind a lock, refreshed when stale.

Runs in a single uvicorn worker, so this in-memory index is the only cache.
Every refresh also rolls forward "repeat after done" tasks that iPhone Reminders
completed (Reminders doesn't know that repeat type).
"""
from __future__ import annotations

import logging
import threading
import time
from contextlib import contextmanager
from typing import Iterator, Optional

from task_caldav_lib import CalDAVService, add_virtual_tags

from .config import get_app_config, get_settings

log = logging.getLogger(__name__)

MAX_AGE_SECONDS = 5.0


class TaskStore:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._svc: Optional[CalDAVService] = None
        self._fetched_at = 0.0
        self.version = 0

    def _service(self) -> CalDAVService:
        if self._svc is None:
            s = get_settings()
            self._svc = CalDAVService(
                s.caldav_url, s.caldav_username, s.caldav_password, s.caldav_calendar,
                tz=get_app_config().timezone, verify_tls=s.caldav_verify_tls,
            )
            self._fetched_at = 0.0
        return self._svc

    @contextmanager
    def service(self, fresh: bool = True) -> Iterator[CalDAVService]:
        """Locked access to the service; refreshes first if the index is stale."""
        with self._lock:
            svc = self._service()
            if fresh and time.monotonic() - self._fetched_at > MAX_AGE_SECONDS:
                self._refresh(svc)
            yield svc

    def _refresh(self, svc: CalDAVService) -> None:
        changed = svc.refresh()
        rolled = svc.reconcile_external_completions()
        if rolled:
            log.info('Rolled forward %d task(s) completed in another client', len(rolled))
        self._fetched_at = time.monotonic()
        if changed or rolled:
            self.version += 1

    def touched(self) -> None:
        """Call after a local write so clients see a new version."""
        self.version += 1

    def task_dicts(self, svc: CalDAVService) -> list[dict]:
        cfg = get_app_config()
        return add_virtual_tags([t.to_dict() for t in svc.tasks()], cfg.tz, cfg.due_this_week_days)

    def task_dict(self, svc: CalDAVService, uid: str) -> dict:
        return next(t for t in self.task_dicts(svc) if t['uid'] == uid)

    def reset(self) -> None:
        with self._lock:
            self._svc = None


store = TaskStore()
