"""Single-administrator sessions for the self-hosted HAP instance."""

from collections.abc import Awaitable, Callable
from hashlib import pbkdf2_hmac
from hmac import compare_digest
from secrets import token_urlsafe
from threading import Lock
from time import time

from fastapi import Request, Response
from fastapi.responses import JSONResponse

from app.core.config.settings import get_settings

COOKIE_NAME = "hap_session"
SESSION_SECONDS = 8 * 60 * 60
_sessions: dict[str, tuple[float, str]] = {}
_failed_logins: dict[str, tuple[int, float]] = {}
_lock = Lock()

_MACHINE_SUFFIXES = frozenset(
    f"/fund/integrations/ttskill/{suffix}"
    for suffix in (
        "base-infos",
        "nav-info",
        "nav-sync-complete",
        "holdings",
        "trades/preview",
        "trades/import",
    )
)


def valid_password_hash(value: str) -> bool:
    try:
        algorithm, rounds, salt, digest = value.split("$")
        return (
            algorithm == "pbkdf2_sha256"
            and 600_000 <= int(rounds) <= 2_000_000
            and len(bytes.fromhex(salt)) >= 16
            and len(bytes.fromhex(digest)) == 32
        )
    except (ValueError, TypeError):
        return False


def verify_password(password: str, encoded: str) -> bool:
    if not valid_password_hash(encoded):
        return False
    _, rounds, salt, digest = encoded.split("$")
    candidate = pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(rounds))
    return compare_digest(candidate, bytes.fromhex(digest))


def login_allowed(address: str) -> bool:
    with _lock:
        failures, blocked_until = _failed_logins.get(address, (0, 0.0))
        return failures < 5 or time() >= blocked_until


def record_login_failure(address: str) -> None:
    with _lock:
        failures, blocked_until = _failed_logins.get(address, (0, 0.0))
        if time() >= blocked_until:
            failures = 0
        failures += 1
        _failed_logins[address] = (failures, time() + 300)


def create_session(address: str) -> tuple[str, str]:
    session_id, csrf = token_urlsafe(32), token_urlsafe(32)
    with _lock:
        _failed_logins.pop(address, None)
        now = time()
        for old_id, (expiry, _) in list(_sessions.items()):
            if expiry <= now:
                del _sessions[old_id]
        _sessions[session_id] = (now + SESSION_SECONDS, csrf)
    return session_id, csrf


def get_session(request: Request) -> tuple[str, str] | None:
    session_id = request.cookies.get(COOKIE_NAME, "")
    with _lock:
        session = _sessions.get(session_id)
        if session is None:
            return None
        expiry, csrf = session
        if expiry <= time():
            del _sessions[session_id]
            return None
    return session_id, csrf


def revoke_session(request: Request) -> None:
    with _lock:
        _sessions.pop(request.cookies.get(COOKIE_NAME, ""), None)


def csrf_matches(request: Request, csrf: str) -> bool:
    supplied = request.headers.get("x-csrf-token", "")
    return bool(supplied) and compare_digest(supplied, csrf)


def allowed_origin(request: Request) -> bool:
    origin = request.headers.get("origin")
    if not origin:
        return True
    settings = get_settings()
    own_origin = f"{request.url.scheme}://{request.headers.get('host', '')}"
    forwarded_scheme = request.headers.get("x-forwarded-proto")
    if forwarded_scheme:
        own_origin = f"{forwarded_scheme}://{request.headers.get('host', '')}"
    return origin == own_origin or origin in settings.cors_origins


def _denied(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"success": False, "code": code, "message": message, "data": None, "trace_id": None},
        headers={"Cache-Control": "no-store"},
    )


async def require_auth(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    path = request.url.path
    prefix = get_settings().api_v1_prefix.rstrip("/")
    protected = path == prefix or path.startswith(prefix + "/") or path in {
        "/docs", "/redoc", "/openapi.json"
    }
    if not protected or request.method == "OPTIONS":
        return await call_next(request)
    if path == prefix + "/system/health" and request.method == "GET":
        return await call_next(request)
    if path == prefix + "/auth/login" and request.method == "POST":
        if not allowed_origin(request):
            return _denied(403, "FORBIDDEN", "Origin is not allowed")
        return await call_next(request)
    if path.removeprefix(prefix) in _MACHINE_SUFFIXES and request.method == "POST":
        return await call_next(request)  # Each route validates its dedicated sync token.
    session = get_session(request)
    if session is None:
        return _denied(401, "UNAUTHORIZED", "Login required")
    if request.method not in {"GET", "HEAD"}:
        if not allowed_origin(request) or not csrf_matches(request, session[1]):
            return _denied(403, "FORBIDDEN", "CSRF validation failed")
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    return response
