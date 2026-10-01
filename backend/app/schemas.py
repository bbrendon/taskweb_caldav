from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from dateutil.parser import isoparse
from dateutil.rrule import rrulestr
from pydantic import BaseModel, ConfigDict, Field, field_validator

from task_caldav_lib import is_valid_interval


def _check_date(v: Optional[str]) -> Optional[str]:
    if v in (None, ''):
        return None
    if len(v) == 10:
        date.fromisoformat(v)
    else:
        isoparse(v)
    return v


class TimeAlarm(BaseModel):
    model_config = ConfigDict(extra='forbid')
    at: Optional[str] = None
    offset: Optional[str] = None
    related: Optional[Literal['START', 'END']] = None

    @field_validator('at')
    @classmethod
    def _v_at(cls, v):
        return _check_date(v)


class LocationAlarm(BaseModel):
    model_config = ConfigDict(extra='forbid')
    title: str = ''
    address: str = ''
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    radius: float = Field(100, ge=10, le=100_000)
    proximity: Literal['ARRIVE', 'DEPART'] = 'ARRIVE'


class TaskFields(BaseModel):
    """Editable task fields. On PATCH only the fields sent are changed."""
    model_config = ConfigDict(extra='forbid')

    title: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = Field(None, max_length=20_000)
    status: Optional[Literal['NEEDS-ACTION', 'IN-PROCESS', 'COMPLETED', 'CANCELLED']] = None
    priority: Optional[int] = Field(None, ge=0, le=9)
    due: Optional[str] = None
    start: Optional[str] = None
    tags: Optional[list[str]] = None
    location: Optional[str] = Field(None, max_length=500)
    url: Optional[str] = Field(None, max_length=2000)
    parent_uid: Optional[str] = None
    starred: Optional[bool] = None
    recur_after: Optional[str] = None
    rrule: Optional[str] = None
    alarms: Optional[list[TimeAlarm]] = None
    location_alarm: Optional[LocationAlarm] = None

    @field_validator('due', 'start')
    @classmethod
    def _v_dates(cls, v):
        return _check_date(v)

    @field_validator('recur_after')
    @classmethod
    def _v_recur(cls, v):
        if v and not is_valid_interval(v):
            raise ValueError("expected an interval like 'P30D', 'P2W', 'P1M'")
        return v or None

    @field_validator('rrule')
    @classmethod
    def _v_rrule(cls, v):
        if v:
            rrulestr(v)
        return v or None

    @field_validator('tags')
    @classmethod
    def _v_tags(cls, v):
        if v is None:
            return v
        seen, out = set(), []
        for t in (x.strip() for x in v):
            if t and t.lower() not in seen:
                seen.add(t.lower())
                out.append(t)
        return out

    def patch(self) -> dict:
        d = self.model_dump(exclude_unset=True)
        if self.recur_after and self.rrule:
            raise ValueError('A task repeats either after completion or on a fixed schedule, not both')
        return d


class LoginBody(BaseModel):
    password: str = Field(max_length=1000)
