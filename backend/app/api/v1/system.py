from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.core.backup.schemas import DatabaseBackupListRead, DatabaseBackupRead
from app.core.backup.scheduler import get_backup_scheduler_status
from app.core.backup.service import DatabaseBackupService
from app.core.config.settings import get_settings
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


@router.get("/backups", response_model=ApiResponse[DatabaseBackupListRead])
def list_database_backups() -> ApiResponse[DatabaseBackupListRead]:
    settings = get_settings()
    service = DatabaseBackupService(settings=settings)
    return ok(service.list_sqlite_backups(scheduler_status=get_backup_scheduler_status()))


@router.post("/backups", response_model=ApiResponse[DatabaseBackupRead])
def create_database_backup() -> ApiResponse[DatabaseBackupRead]:
    settings = get_settings()
    service = DatabaseBackupService(settings=settings)
    return ok(service.create_sqlite_backup(), message="backup created")


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
