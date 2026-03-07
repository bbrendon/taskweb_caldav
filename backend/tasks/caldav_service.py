"""
Thin Django wrapper around task_caldav_lib.CalDAVService.
Reads credentials from Django settings and manages the module-level singleton.
"""
from django.conf import settings
from task_caldav_lib.service import CalDAVService

_service_instance = None


def get_service() -> CalDAVService:
    global _service_instance
    if _service_instance is None:
        _service_instance = CalDAVService(
            url=settings.CALDAV_URL,
            username=settings.CALDAV_USERNAME,
            password=settings.CALDAV_PASSWORD,
            calendar_name=settings.CALDAV_CALENDAR,
        )
    return _service_instance
