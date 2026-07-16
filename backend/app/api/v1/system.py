from fastapi import APIRouter

from app.core.backup.schemas import DatabaseBackupListRead, DatabaseBackupRead
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
    return ok(service.list_sqlite_backups())


@router.post("/backups", response_model=ApiResponse[DatabaseBackupRead])
def create_database_backup() -> ApiResponse[DatabaseBackupRead]:
    settings = get_settings()
    service = DatabaseBackupService(settings=settings)
    return ok(service.create_sqlite_backup(), message="backup created")
