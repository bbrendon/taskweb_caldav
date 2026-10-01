"""
App config (read-only, from YAML) and user settings (saved searches, column layouts).

User settings are a free-form JSON document owned by the frontend, stored in
DATA_DIR/settings.json so every device sees the same views.
"""
from __future__ import annotations

import json
import os
import tempfile
import threading

from fastapi import APIRouter, Body, Depends, HTTPException

from task_caldav_lib import PRIORITY_BY_BAND, VIRTUAL_TAGS

from ..auth import require_session
from ..config import get_app_config, get_settings

router = APIRouter(prefix='/api', dependencies=[Depends(require_session)])

MAX_SETTINGS_BYTES = 512 * 1024
_lock = threading.Lock()


@router.get('/config')
def app_config():
    cfg = get_app_config()
    return {
        'timezone': cfg.timezone,
        'due_this_week_days': cfg.due_this_week_days,
        'tags': cfg.tags,
        'places': [p.model_dump() for p in cfg.places],
        'priorities': PRIORITY_BY_BAND,
        'virtual_tags': list(VIRTUAL_TAGS),
    }


def _path():
    return get_settings().data_dir / 'settings.json'


@router.get('/settings')
def read_settings():
    path = _path()
    if not path.exists():
        return {}
    return json.loads(path.read_text())


@router.put('/settings')
def write_settings(doc: dict = Body(...)):
    raw = json.dumps(doc, ensure_ascii=False, indent=1)
    if len(raw.encode()) > MAX_SETTINGS_BYTES:
        raise HTTPException(413, 'Settings document too large')
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        fd, tmp = tempfile.mkstemp(dir=path.parent, prefix='.settings-')
        with os.fdopen(fd, 'w') as f:
            f.write(raw)
        os.replace(tmp, path)
    return doc
