from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.core.backup.schemas import (
    DatabaseBackupListRead,
    DatabaseBackupRead,
    DatabaseRestoreRead,
    DatabaseRestoreRequest,
)
from app.core.backup.scheduler import get_backup_scheduler_status, upload_remote_backup
from app.core.backup.service import DatabaseBackupService
from app.core.config.settings import get_settings
from app.core.notification.schemas import (
    NotificationStatusRead,
    NotificationTestRequest,
    NotificationTestResult,
)
from app.core.notification.service import NotificationService
from app.shared.exceptions.base import AppError
from app.shared.exceptions.codes import ErrorCode
from app.shared.responses.schemas import ApiResponse, ok

router = APIRouter()


@router.get("/health", response_model=ApiResponse[dict[str, str]])
def health_check() -> ApiResponse[dict[str, str]]:
    settings = get_settings()
    return ok(
        {
            "status": "ok",
            "version": settings.app_version,
            "database": "ok",
        }
    )


@router.get("/notifications", response_model=ApiResponse[NotificationStatusRead])
def get_notification_status() -> ApiResponse[NotificationStatusRead]:
    settings = get_settings()
    service = NotificationService(settings=settings)
    return ok(service.get_status())


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
