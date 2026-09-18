"""POST /auth/login, POST /auth/logout -- security_nfr SEC-1/SEC-2/SEC-5,
data_integration decisions DAT-10/DAT-11."""
import secrets

from fastapi import APIRouter, Cookie, HTTPException, Request, Response

from app.auth import (
    SESSION_COOKIE_NAME,
    clear_session_cookie,
    client_key_from_request,
    create_session,
    invalidate_session,
    is_locked_out,
    record_login_failure,
    record_login_success,
    require_session,
    set_session_cookie,
)
from app.config import get_settings
from app.schemas import (
    ErrorCode,
    ErrorResponse,
    LoginRequest,
    LoginResponse,
    LogoutResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, request: Request, response: Response):
    client_key = client_key_from_request(request)
    if is_locked_out(client_key):
        raise HTTPException(
            status_code=429,
            headers={"Retry-After": "900"},
            detail=ErrorResponse(error_code=ErrorCode.LOGIN_LOCKED, message="Too many failed attempts. Try again later.").model_dump(),
        )

    settings = get_settings()
    # Constant-time comparison against a fixed shared secret (SEC-1) -- `!=`
    # on a str is short-circuiting and leaks timing information about how
    # many leading characters matched.
    username_ok = secrets.compare_digest(payload.username, settings.shared_username)
    password_ok = secrets.compare_digest(payload.password, settings.shared_password)
    if not (username_ok and password_ok):
        record_login_failure(client_key)
        raise HTTPException(
            status_code=401,
            detail=ErrorResponse(error_code=ErrorCode.INVALID_CREDENTIALS, message="Incorrect username or password.").model_dump(),
        )

    record_login_success(client_key)
    token = create_session()
    set_session_cookie(response, token)
    return LoginResponse(authenticated=True)


@router.post("/logout", response_model=LogoutResponse)
def logout(response: Response, session: str = Cookie(default=None, alias=SESSION_COOKIE_NAME)):
    # require_session as a plain call so we get the same 401 shape on no session.
    require_session(session)
    invalidate_session(session)
    clear_session_cookie(response)
    return LogoutResponse(invalidated=True)
