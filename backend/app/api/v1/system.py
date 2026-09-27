from pathlib import Path

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse
from loguru import logger
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.backup.scheduler import get_backup_scheduler_status, upload_remote_backup
from app.core.backup.schemas import (
    DatabaseBackupListRead,
    DatabaseBackupRead,
    DatabaseRestoreRead,
    DatabaseRestoreRequest,
)
from app.core.backup.service import DatabaseBackupService
from app.core.config.settings import get_settings
from app.core.database import session as database
from app.core.database.maintenance import database_maintenance
from app.core.infrastructure_health.scheduler import get_infrastructure_health_scheduler_status
from app.core.infrastructure_health.schemas import InfrastructureHealthRead
from app.core.infrastructure_health.service import InfrastructureHealthService
from app.core.notification.schemas import (
    NotificationDeliveryRunPageRead,
    NotificationStatusRead,
    NotificationTestRequest,
    NotificationTestResult,
)
from app.core.notification.service import NotificationService
from app.shared.exceptions.base import AppError
from app.shared.exceptions.codes import ErrorCode
from app.shared.responses.schemas import ApiResponse, ok

router = APIRouter()


@router.get("/restore-status", response_model=ApiResponse[dict[str, object]])
def get_restore_status() -> ApiResponse[dict[str, object]]:
    return ok(database_maintenance.status())


@router.get("/infrastructure-health", response_model=ApiResponse[InfrastructureHealthRead])
def get_infrastructure_health() -> ApiResponse[InfrastructureHealthRead]:
    settings = get_settings()
    return ok(InfrastructureHealthService(settings).check())


@router.get("/infrastructure-health/scheduler", response_model=ApiResponse[dict[str, object]])
def get_infrastructure_health_scheduler() -> ApiResponse[dict[str, object]]:
    return ok(get_infrastructure_health_scheduler_status())


@router.get("/health", response_model=ApiResponse[dict[str, str]])
def health_check() -> ApiResponse[dict[str, str]]:
    settings = get_settings()
    database_status = _database_readiness()
    return ok(
        {
            "status": "ok" if database_status == "ok" else "degraded",
            "version": settings.app_version,
            "git_sha": settings.app_build_sha,
            "git_commit": settings.app_build_sha,
            "build_time": settings.app_build_time,
            "image": settings.app_image_reference,
            "environment": settings.app_deployment_environment,
            "database": database_status,
        }
    )


def _database_readiness() -> str:
    # Health bypasses the middleware gate, but its DB access must still drain before restore.
    with database_maintenance.activity() as admitted:
        if not admitted:
            return "maintenance"
        try:
            engine = database.engine
            if engine.url.get_backend_name() == "sqlite":
                path = engine.url.database
                if path and path != ":memory:" and not Path(path).is_file():
                    # SQLite's default connect would silently create a missing database.
                    logger.bind(reason="DB_FILE_UNAVAILABLE").warning("Health database probe: DB_FILE_UNAVAILABLE")
                    return "error"
            with engine.connect() as connection:
                connection.execute(text("SELECT 1")).scalar_one()
            return "ok"
        except (SQLAlchemyError, OSError):
            logger.bind(reason="DB_PROBE_FAILED").warning("Health database probe: DB_PROBE_FAILED")
            return "error"


@router.get("/build-info", response_model=ApiResponse[dict[str, str]])
def build_info() -> ApiResponse[dict[str, str]]:
    settings = get_settings()
    return ok(
        {
            "app": settings.app_name,
            "service": "hap-backend",
            "git_sha": settings.app_build_sha,
            "git_commit": settings.app_build_sha,
            "build_time": settings.app_build_time,
            "image": settings.app_image_reference,
            "environment": settings.app_deployment_environment,
            "version": settings.app_version,
        }
    )


@router.get("/notifications", response_model=ApiResponse[NotificationStatusRead])
def get_notification_status() -> ApiResponse[NotificationStatusRead]:
    settings = get_settings()
    service = NotificationService(settings=settings)
    return ok(service.get_status())


@router.get("/notifications/runs", response_model=ApiResponse[NotificationDeliveryRunPageRead])
def list_notification_runs(
    limit: int = Query(default=20, ge=1, le=100),
) -> ApiResponse[NotificationDeliveryRunPageRead]:
    settings = get_settings()
    service = NotificationService(settings=settings)
    return ok(service.list_delivery_runs(limit=limit))


@router.post("/notifications/test", response_model=ApiResponse[NotificationTestResult])
def test_notification(
    payload: NotificationTestRequest,
) -> ApiResponse[NotificationTestResult]:
    settings = get_settings()
    service = NotificationService(settings=settings)
    result = service.send_test(
        channel=payload.channel,
        title=payload.title,
        message=payload.message,
    )
    return ok(result, message="notification test finished")


@router.get("/backups", response_model=ApiResponse[DatabaseBackupListRead])
def list_database_backups() -> ApiResponse[DatabaseBackupListRead]:
    settings = get_settings()
    service = DatabaseBackupService(settings=settings)
    return ok(service.list_sqlite_backups(scheduler_status=get_backup_scheduler_status()))


@router.post("/backups", response_model=ApiResponse[DatabaseBackupRead])
def create_database_backup() -> ApiResponse[DatabaseBackupRead]:
    settings = get_settings()
    service = DatabaseBackupService(settings=settings)
    backup = service.create_sqlite_backup()
    backup_path = service.get_sqlite_backup_path(backup.file_name)
    upload_remote_backup(backup=backup, backup_path=backup_path, trigger_type="manual")
    return ok(backup, message="backup created")


@router.post("/backups/{file_name}/restore", response_model=ApiResponse[DatabaseRestoreRead])
def restore_database_backup(
    file_name: str,
    payload: DatabaseRestoreRequest,
) -> ApiResponse[DatabaseRestoreRead]:
    if payload.file_name != file_name:
        raise AppError(
            code=ErrorCode.validation_error,
            message="Restore payload file_name must match request path.",
            status_code=400,
        )
    settings = get_settings()
    service = DatabaseBackupService(settings=settings)
    result = service.restore_sqlite_backup(
        file_name=file_name,
        confirmation=payload.confirmation,
    )
    return ok(result, message="database restored")


@router.get("/backups/{file_name}/download")
def download_database_backup(file_name: str) -> FileResponse:
    settings = get_settings()
    service = DatabaseBackupService(settings=settings)
    path = service.get_sqlite_backup_path(file_name)
    return FileResponse(
        path=path,
        filename=file_name,
        media_type="application/octet-stream",
    )
