from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel


PRIORITY_LABEL = {0: "none", 1: "H", 5: "M", 9: "L"}
PRIORITY_VALUE = {"none": 0, "H": 1, "M": 5, "L": 9}


class TaskLocation(BaseModel):
    title: str
    address: str = ""
    lat: Optional[float] = None  # None for CarPlay CONNECT/DISCONNECT triggers
    lng: Optional[float] = None
    proximity: str = "ARRIVE"


class Task(BaseModel):
    uid: str
    title: str
    description: Optional[str] = None
    due: Optional[date] = None
    priority: int = 0  # 0=none, 1=high, 5=medium, 9=low
    tags: list[str] = []
    status: str = "NEEDS-ACTION"  # NEEDS-ACTION | IN-PROCESS | COMPLETED | CANCELLED
    recurrence: Optional[str] = None  # RRULE string
    completed: Optional[datetime] = None
    calendar_name: Optional[str] = None
    location_alarm: Optional[TaskLocation] = None

    @property
    def priority_label(self) -> str:
        return PRIORITY_LABEL.get(self.priority, "none")

    @property
    def is_completed(self) -> bool:
        return self.status == "COMPLETED"

    @property
    def is_overdue(self) -> bool:
        if self.due is None or self.is_completed:
            return False
        return self.due < date.today()

    @property
    def is_due_today(self) -> bool:
        if self.due is None:
            return False
        return self.due == date.today()

    @property
    def is_favorite(self) -> bool:
        return "fav" in self.tags


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    due: Optional[date] = None
    priority: int = 0
    tags: list[str] = []
    status: str = "NEEDS-ACTION"
    recurrence: Optional[str] = None
    location_alarm: Optional[TaskLocation] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due: Optional[date] = None
    priority: Optional[int] = None
    tags: Optional[list[str]] = None
    status: Optional[str] = None
    recurrence: Optional[str] = None
    location_alarm: Optional[TaskLocation] = None
