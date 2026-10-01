"""
Single-user, password-only auth.

The password is checked against an argon2 hash (APP_PASSWORD_HASH). A successful
login sets a signed, HttpOnly session cookie. Mutating API requests must also carry
`X-Requested-With: taskweb`, which a cross-site form post cannot add (CSRF defense on
top of SameSite=Lax).
"""
from __future__ import annotations

import logging
import secrets
import time
from collections import defaultdict, deque

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import HTTPException, Request, Response
from itsdangerous import BadSignature, SignatureExpired, TimestampSigner

from .config import get_settings

log = logging.getLogger(__name__)

COOKIE = 'tw_session'
CSRF_HEADER = 'x-requested-with'
CSRF_VALUE = 'taskweb'
LOGIN_ATTEMPTS = 5
LOGIN_WINDOW = 60.0

_hasher = PasswordHasher()
_attempts: dict[str, deque] = defaultdict(deque)
_dev_secret = secrets.token_urlsafe(32)


def _signer() -> TimestampSigner:
    secret = get_settings().session_secret
    if not secret:
        log.warning('SESSION_SECRET not set; using a random one (sessions end on restart)')
        secret = _dev_secret
    return TimestampSigner(secret, salt='taskweb-session')


def check_password(password: str) -> bool:
    hashed = get_settings().app_password_hash
    if not hashed:
        log.error('APP_PASSWORD_HASH is not set; login is disabled')
        return False
    try:
        return _hasher.verify(hashed, password)
    except (VerificationError, InvalidHashError):
        return False


def rate_limited(ip: str) -> bool:
    """Record a login attempt; True if this IP exceeded the limit."""
    now = time.monotonic()
    q = _attempts[ip]
    while q and now - q[0] > LOGIN_WINDOW:
        q.popleft()
    q.append(now)
    return len(q) > LOGIN_ATTEMPTS


def start_session(response: Response) -> None:
    s = get_settings()
    response.set_cookie(
        COOKIE, _signer().sign('user').decode(),
        max_age=s.session_days * 86400, httponly=True, secure=s.cookie_secure, samesite='lax', path='/',
    )


def end_session(response: Response) -> None:
    response.delete_cookie(COOKIE, path='/')


def is_authenticated(request: Request) -> bool:
    token = request.cookies.get(COOKIE)
    if not token:
        return False
    try:
        _signer().unsign(token, max_age=get_settings().session_days * 86400)
        return True
    except (BadSignature, SignatureExpired):
        return False


def require_session(request: Request) -> None:
    """FastAPI dependency for protected routes."""
    if not is_authenticated(request):
        raise HTTPException(401, 'Not logged in')
    if request.method not in ('GET', 'HEAD', 'OPTIONS') and request.headers.get(CSRF_HEADER) != CSRF_VALUE:
        raise HTTPException(403, 'Missing X-Requested-With header')
