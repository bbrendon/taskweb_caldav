from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from task_caldav_lib import CalDAVService, TaskNotFound

from ..auth import require_session
from ..schemas import TaskFields
from ..store import store

router = APIRouter(prefix='/api/tasks', dependencies=[Depends(require_session)])


def _validated_patch(body: TaskFields, svc: CalDAVService, uid: Optional[str] = None) -> dict:
    try:
        patch = body.patch()
    except ValueError as e:
        raise HTTPException(422, str(e))
    # The two repeat kinds are exclusive: setting one clears the other.
    if patch.get('recur_after'):
        patch['rrule'] = None
    if patch.get('rrule'):
        patch['recur_after'] = None
    parent = patch.get('parent_uid')
    if parent:
        try:
            svc.get(parent)
        except TaskNotFound:
            raise HTTPException(422, 'Parent task does not exist')
        if uid and (parent == uid or parent in {t.uid for t in svc.descendants(uid)}):
            raise HTTPException(422, 'A task cannot be nested under itself or its subtasks')
    return patch


@router.get('')
def list_tasks(since: Optional[int] = Query(None, description='Last version the client has')):
    with store.service() as svc:
        if since is not None and since == store.version:
            return {'version': store.version, 'unchanged': True}
        return {'version': store.version, 'tasks': store.task_dicts(svc)}


@router.post('', status_code=201)
def create_task(body: TaskFields):
    with store.service() as svc:
        task = svc.create(_validated_patch(body, svc))
        store.touched()
        return store.task_dict(svc, task.uid)


@router.patch('/{uid}')
def update_task(uid: str, body: TaskFields):
    with store.service() as svc:
        svc.update(uid, _validated_patch(body, svc, uid))
        store.touched()
        return store.task_dict(svc, uid)


@router.delete('/{uid}')
def delete_task(uid: str, children: Literal['orphan', 'delete'] = 'orphan'):
    with store.service() as svc:
        deleted = svc.delete(uid, children)
        store.touched()
        return {'deleted': deleted}


@router.post('/{uid}/complete')
def complete_task(uid: str):
    with store.service() as svc:
        svc.complete(uid)
        store.touched()
        return store.task_dict(svc, uid)


@router.post('/{uid}/reopen')
def reopen_task(uid: str):
    with store.service() as svc:
        svc.reopen(uid)
        store.touched()
        return store.task_dict(svc, uid)


@router.post('/{uid}/skip')
def skip_task(uid: str):
    with store.service() as svc:
        try:
            svc.skip(uid)
        except ValueError as e:
            raise HTTPException(422, str(e))
        store.touched()
        return store.task_dict(svc, uid)
