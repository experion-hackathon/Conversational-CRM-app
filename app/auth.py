"""SharedLoginAuth -- single shared credential exchanged for an opaque session
token (security_nfr SEC-1), session lifecycle (SEC-2), login lockout (SEC-5),
and per-session rate limiting (SEC-11), per data_integration decisions
DAT-10/DAT-11 and the API-CONTRACT's `SharedLoginAuth` security scheme.

Session/lockout/rate-limit state is held in-process, in memory. This is a
disclosed limitation (mirrors security_nfr's own Open Item OI-18: "where
session state actually lives at runtime" was never decided by any
discipline) -- correct for this demo's single-process deployment, not
durable across a restart or safe for a multi-process deployment without
further work.
"""
from __future__ import annotations

import secrets
import time
from dataclasses import dataclass, field

from fastapi import Cookie, HTTPException, Request, Response

from app.config import get_settings
from app.schemas import ErrorCode, ErrorResponse

SESSION_COOKIE_NAME = "session"
IDLE_TIMEOUT_SECONDS = 2 * 60 * 60
ABSOLUTE_TIMEOUT_SECONDS = 12 * 60 * 60


@dataclass
class _Session:
    created_at: float
    last_seen_at: float


@dataclass
class _LockoutState:
    failures: list[float] = field(default_factory=list)


_sessions: dict[str, _Session] = {}
_lockouts: dict[str, _LockoutState] = {}
_rate_windows: dict[str, list[float]] = {}


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=401,
        detail=ErrorResponse(error_code=ErrorCode.UNAUTHENTICATED, message="No valid session. Please log in.").model_dump(),
    )


def reset_state_for_tests():
    _sessions.clear()
    _lockouts.clear()
    _rate_windows.clear()


def is_locked_out(client_key: str) -> bool:
    settings = get_settings()
    state = _lockouts.get(client_key)
    if not state:
        return False
    window_start = time.time() - settings.login_lockout_window_minutes * 60
    state.failures = [t for t in state.failures if t >= window_start]
    return len(state.failures) >= settings.login_lockout_attempts


def record_login_failure(client_key: str) -> None:
    _lockouts.setdefault(client_key, _LockoutState()).failures.append(time.time())


def record_login_success(client_key: str) -> None:
    _lockouts.pop(client_key, None)


def create_session() -> str:
    token = secrets.token_urlsafe(32)
    now = time.time()
    _sessions[token] = _Session(created_at=now, last_seen_at=now)
    return token


def invalidate_session(token: str) -> None:
    _sessions.pop(token, None)


def _validate_and_touch(token: str) -> bool:
    session = _sessions.get(token)
    if session is None:
        return False
    now = time.time()
    if now - session.created_at > ABSOLUTE_TIMEOUT_SECONDS:
        _sessions.pop(token, None)
        return False
    if now - session.last_seen_at > IDLE_TIMEOUT_SECONDS:
        _sessions.pop(token, None)
        return False
    session.last_seen_at = now
    return True


def require_session(session: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME)) -> str:
    """FastAPI dependency enforcing SharedLoginAuth on every protected operation."""
    if not session or not _validate_and_touch(session):
        raise _unauthorized()
    return session


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=ABSOLUTE_TIMEOUT_SECONDS,
    )


def clear_session_cookie(response: Response) -> None:
    response.set_cookie(key=SESSION_COOKIE_NAME, value="", max_age=0)


def check_rate_limit(session_token: str) -> None:
    """SEC-11/NFR-10: per-session request rate limit on the three
    Bedrock-invoking operations (POST /interactions, /qa, /briefs).
    """
    settings = get_settings()
    now = time.time()
    window = _rate_windows.setdefault(session_token, [])
    window[:] = [t for t in window if now - t < 60]
    if len(window) >= settings.rate_limit_per_minute:
        raise HTTPException(
            status_code=429,
            headers={"Retry-After": "60"},
            detail=ErrorResponse(error_code=ErrorCode.RATE_LIMITED, message="Too many requests. Please slow down.").model_dump(),
        )
    window.append(now)


def client_key_from_request(request: Request) -> str:
    return request.client.host if request.client else "unknown"
