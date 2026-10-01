"""
TaskWeb API + SPA host.

    uvicorn app.main:app --workers 1 --proxy-headers --forwarded-allow-ips='*'

Must run as a single worker: the task index lives in process memory.
"""
from __future__ import annotations

import logging

import caldav.lib.error as caldav_errors
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from task_caldav_lib import ConflictError, TaskNotFound

from . import auth
from .api import settings as settings_api
from .api import tasks as tasks_api
from .config import get_settings
from .schemas import LoginBody
from .store import store

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
log = logging.getLogger('taskweb')

app = FastAPI(title='TaskWeb', docs_url=None, redoc_url=None, openapi_url=None)
app.include_router(tasks_api.router)
app.include_router(settings_api.router)


@app.exception_handler(TaskNotFound)
def _not_found(request: Request, exc: TaskNotFound):
    return JSONResponse({'detail': 'Task not found'}, status_code=404)


@app.exception_handler(ConflictError)
def _conflict(request: Request, exc: ConflictError):
    return JSONResponse({'detail': 'The task changed on another device. Refresh and try again.'}, status_code=409)


@app.exception_handler(caldav_errors.DAVError)
def _dav_error(request: Request, exc: Exception):
    log.exception('CalDAV error')
    store.reset()
    return JSONResponse({'detail': 'Calendar server error. Try again shortly.'}, status_code=503)


@app.exception_handler(OSError)
def _network_error(request: Request, exc: Exception):
    log.exception('Network error talking to CalDAV')
    store.reset()
    return JSONResponse({'detail': 'Calendar server unreachable.'}, status_code=503)


# ------------------------------------------------------------------ auth

@app.post('/api/login')
def login(body: LoginBody, request: Request, response: Response):
    ip = request.client.host if request.client else 'unknown'
    if auth.rate_limited(ip):
        raise HTTPException(429, 'Too many attempts. Wait a minute.')
    if not auth.check_password(body.password):
        raise HTTPException(401, 'Wrong password')
    auth.start_session(response)
    return {'ok': True}


@app.post('/api/logout')
def logout(response: Response):
    auth.end_session(response)
    return {'ok': True}


@app.get('/api/session')
def session(request: Request):
    return {'authenticated': auth.is_authenticated(request)}


@app.get('/api/health')
def health():
    return {'ok': True}


# ------------------------------------------------------------------ SPA

_static = get_settings().static_dir
if (_static / 'assets').is_dir():
    app.mount('/assets', StaticFiles(directory=_static / 'assets'), name='assets')


@app.get('/{path:path}', include_in_schema=False)
def spa(path: str):
    if path.startswith('api/'):
        raise HTTPException(404)
    candidate = (_static / path).resolve()
    if path and candidate.is_file() and candidate.is_relative_to(_static.resolve()):
        # sw.js and manifest must revalidate so updates roll out; hashed assets are under /assets
        return FileResponse(candidate, headers={'Cache-Control': 'no-cache'})
    index = _static / 'index.html'
    if not index.exists():
        return JSONResponse({'detail': 'Frontend not built. Run the Vite dev server or `npm run build`.'}, 404)
    return FileResponse(index, headers={'Cache-Control': 'no-cache'})
