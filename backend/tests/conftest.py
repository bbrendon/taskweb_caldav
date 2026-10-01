import os
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path

import pytest
from argon2 import PasswordHasher

PASSWORD = 'correct horse battery'


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


@pytest.fixture(scope='session')
def radicale_url(tmp_path_factory):
    port = _free_port()
    storage = tmp_path_factory.mktemp('radicale')
    proc = subprocess.Popen(
        [sys.executable, '-m', 'radicale', f'--storage-filesystem-folder={storage}',
         '--auth-type=none', f'--server-hosts=127.0.0.1:{port}', '--logging-level=warning'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            socket.create_connection(('127.0.0.1', port), timeout=0.2).close()
            break
        except OSError:
            time.sleep(0.1)
    yield f'http://127.0.0.1:{port}/'
    proc.terminate()
    proc.wait()


@pytest.fixture
def client(radicale_url, tmp_path, monkeypatch):
    """App wired to a fresh calendar, temp data dir and a test config."""
    from task_caldav_lib import CalDAVService

    calendar = f'Tasks-{uuid.uuid4().hex[:8]}'
    CalDAVService(radicale_url, 'test', 'x', calendar, create_calendar=True)
    cfg = tmp_path / 'taskweb.yaml'
    cfg.write_text(
        'timezone: America/Los_Angeles\n'
        'tags: [Home, Work]\n'
        'places:\n  - {name: Home, address: 1 Main St, lat: 37.33, lon: -122.03, radius: 120}\n'
    )
    env = {
        'CALDAV_URL': radicale_url, 'CALDAV_USERNAME': 'test', 'CALDAV_PASSWORD': 'x',
        'CALDAV_CALENDAR': calendar, 'APP_PASSWORD_HASH': PasswordHasher().hash(PASSWORD),
        'SESSION_SECRET': 'test-secret', 'COOKIE_SECURE': 'false',
        'TASKWEB_CONFIG': str(cfg), 'DATA_DIR': str(tmp_path / 'data'),
    }
    for k, v in env.items():
        monkeypatch.setenv(k, v)

    from app import auth, config
    from app.store import store
    config.get_settings.cache_clear()
    config.get_app_config.cache_clear()
    auth._attempts.clear()
    store.reset()

    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture
def authed(client):
    r = client.post('/api/login', json={'password': PASSWORD})
    assert r.status_code == 200
    client.headers['X-Requested-With'] = 'taskweb'
    return client
