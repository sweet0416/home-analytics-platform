from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, Field

from app.core.auth import (
    COOKIE_NAME,
    SESSION_SECONDS,
    create_session,
    get_session,
    login_allowed,
    record_login_failure,
    revoke_session,
    verify_password,
)
from app.core.config.settings import get_settings
from app.shared.exceptions.base import AppError
from app.shared.exceptions.codes import ErrorCode
from app.shared.responses.schemas import ApiResponse, ok

router = APIRouter()


class LoginRequest(BaseModel):
    username: str = Field(max_length=64)
    password: str = Field(max_length=1024)


@router.post("/login", response_model=ApiResponse[dict[str, str]])
def login(
    payload: LoginRequest, request: Request, response: Response
) -> ApiResponse[dict[str, str]]:
    address = request.client.host if request.client else "unknown"
    if not login_allowed(address):
        raise AppError(ErrorCode.validation_error, "Too many login attempts", status_code=429)
    if payload.username != "admin" or not verify_password(
        payload.password, get_settings().admin_password_hash()
    ):
        record_login_failure(address)
        raise AppError(ErrorCode.validation_error, "Invalid credentials", status_code=401)
    session_id, csrf = create_session(address)
    response.set_cookie(
        COOKIE_NAME,
        session_id,
        max_age=SESSION_SECONDS,
        httponly=True,
        secure=get_settings().hap_cookie_secure
        or request.url.scheme == "https"
        or request.headers.get("x-forwarded-proto") == "https",
        samesite="strict",
        path="/",
    )
    response.headers["Cache-Control"] = "no-store"
    return ok({"username": "admin", "role": "admin", "csrf_token": csrf})


@router.get("/me", response_model=ApiResponse[dict[str, str]])
def me(request: Request, response: Response) -> ApiResponse[dict[str, str]]:
    session = get_session(request)
    if session is None:
        raise AppError(ErrorCode.validation_error, "Login required", status_code=401)
    response.headers["Cache-Control"] = "no-store"
    return ok({"username": "admin", "role": "admin", "csrf_token": session[1]})


@router.post("/logout", response_model=ApiResponse[dict[str, bool]])
def logout(request: Request, response: Response) -> ApiResponse[dict[str, bool]]:
    revoke_session(request)
    response.delete_cookie(COOKIE_NAME, path="/")
    response.headers["Cache-Control"] = "no-store"
    return ok({"logged_out": True})
