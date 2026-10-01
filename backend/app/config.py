"""
Configuration.

Secrets and connection details come from environment variables (or the repo's .env);
user-editable preferences (time zone, tags, preset places) come from a YAML file.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

import yaml
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=REPO_ROOT / '.env', extra='ignore')

    caldav_url: str
    caldav_username: str = ''
    caldav_password: str = ''
    caldav_calendar: str = 'Tasks'
    caldav_verify_tls: bool = True

    app_password_hash: str = ''
    session_secret: str = ''
    session_days: int = 180
    cookie_secure: bool = True

    taskweb_config: Path = REPO_ROOT / 'config' / 'taskweb.yaml'
    data_dir: Path = REPO_ROOT / 'data'
    static_dir: Path = Path(__file__).resolve().parent / 'static'


class Place(BaseModel):
    name: str
    address: str = ''
    lat: float
    lon: float
    radius: float = 100


class AppConfig(BaseModel):
    timezone: str = 'UTC'
    due_this_week_days: int = Field(7, ge=1, le=31)
    tags: list[str] = []
    places: list[Place] = []

    @field_validator('timezone')
    @classmethod
    def _valid_tz(cls, v: str) -> str:
        ZoneInfo(v)
        return v

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def get_app_config(path: Optional[Path] = None) -> AppConfig:
    path = path or get_settings().taskweb_config
    if not path.exists():
        return AppConfig()
    return AppConfig.model_validate(yaml.safe_load(path.read_text()) or {})
