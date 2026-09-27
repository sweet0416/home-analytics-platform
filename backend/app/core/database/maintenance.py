"""Single-worker database quiescence, including response cleanup/background tasks."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
from pathlib import Path
from threading import Condition
from uuid import uuid4

from loguru import logger
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.shared.exceptions.base import AppError
from app.shared.exceptions.codes import ErrorCode


def restore_marker(database_path: Path) -> Path:
    return database_path.with_name(database_path.name + ".restore-in-progress")


def require_recovered_database(database_path: Path) -> None:
    if restore_marker(database_path).exists():
        raise RuntimeError("RESTORE_RECOVERY_REQUIRED: inspect the restore audit before startup")


class DatabaseMaintenance:
    def __init__(self) -> None:
        self._condition = Condition()
        self._depth: ContextVar[int] = ContextVar("database_activity_depth", default=0)
        self._active = 0
        self._blocked = False
        self._phase = "IDLE"
        self._operation_id: str | None = None
        self._result: dict[str, str] = {}

    @contextmanager
    def activity(self) -> Iterator[bool]:
        # Nested calls inherit the outer lease (also in AnyIO worker threads).
        if self._depth.get():
            yield True
            return
        with self._condition:
            admitted = not self._blocked
            if admitted:
                self._active += 1
        if not admitted:
            yield False
            return
        token = self._depth.set(1)
        try:
            yield True
        finally:
            self._depth.reset(token)
            with self._condition:
                self._active -= 1
                self._condition.notify_all()

    def begin_restore(self) -> str:
        with self._condition:
            if self._blocked or self._depth.get():
                raise AppError(ErrorCode.conflict, "RESTORE_IN_PROGRESS_OR_RECOVERY_REQUIRED", 409)
            self._blocked = True
            self._phase = "PREPARING"
            self._operation_id = uuid4().hex
            self._result = {}
            return self._operation_id

    def drain(self, timeout: float = 10.0) -> None:
        with self._condition:
            if not self._condition.wait_for(lambda: self._active == 0, timeout=timeout):
                raise AppError(
                    ErrorCode.conflict, "RESTORE_BUSY: active database work did not finish", 409
                )
            self._phase = "MAINTENANCE"

    def transition(self, phase: str) -> None:
        with self._condition:
            self._phase = phase

    def finish(self, phase: str, *, usable: bool, result: dict[str, str] | None = None) -> None:
        with self._condition:
            self._phase = phase
            self._blocked = not usable
            self._result = result or {}
            self._condition.notify_all()

    def status(self) -> dict[str, object]:
        with self._condition:
            return {
                "phase": self._phase,
                "maintenance": self._blocked,
                "operation_id": self._operation_id,
                "active_operations": self._active,
                "result": dict(self._result),
            }


# ponytail: one process only; multi-worker deployment requires a different coordination design.
database_maintenance = DatabaseMaintenance()


def guarded_job(function: Callable) -> Callable:
    @wraps(function)
    def guarded(*args, **kwargs):
        with database_maintenance.activity() as admitted:
            if not admitted:
                logger.info(
                    "database_job={} result=skipped reason=restore_maintenance", function.__name__
                )
                return None
            return function(*args, **kwargs)

    return guarded


class DatabaseMaintenanceMiddleware:
    def __init__(self, app: ASGIApp, *, prefix: str) -> None:
        self.app = app
        self.prefix = prefix.rstrip("/")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        path = scope.get("path", "")
        method = scope.get("method", "")
        safe = method in {"GET", "HEAD"} and path in {
            self.prefix + "/system/health",
            self.prefix + "/system/restore-status",
            self.prefix + "/system/build-info",
            self.prefix + "/auth/me",
        }
        restore = (
            method == "POST"
            and path.startswith(self.prefix + "/system/backups/")
            and path.endswith("/restore")
        )
        session_action = method == "POST" and path in {
            self.prefix + "/auth/login",
            self.prefix + "/auth/logout",
        }
        if scope["type"] != "http" or safe or restore or session_action:
            await self.app(scope, receive, send)
            return
        with database_maintenance.activity() as admitted:
            if not admitted:
                response = JSONResponse(
                    {
                        "success": False,
                        "code": "DATABASE_MAINTENANCE",
                        "message": "Database restore maintenance; check restore status before retrying.",
                        "data": None,
                        "trace_id": scope.get("state", {}).get("trace_id"),
                    },
                    status_code=503,
                    headers={"Retry-After": "5", "Cache-Control": "no-store"},
                )
                await response(scope, receive, send)
                return
            # Pure ASGI: keep the lease through dependency teardown, streams and BackgroundTasks.
            await self.app(scope, receive, send)
