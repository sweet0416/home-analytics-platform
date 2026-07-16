import sqlite3
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote

from loguru import logger

from app.core.backup.schemas import DatabaseBackupListRead, DatabaseBackupRead
from app.core.config.settings import Settings
from app.shared.exceptions.base import AppError
from app.shared.exceptions.codes import ErrorCode


class DatabaseBackupService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def create_sqlite_backup(self) -> DatabaseBackupRead:
        source_path = self._get_sqlite_database_path()
        if not source_path.exists():
            raise AppError(
                code=ErrorCode.not_found,
                message=f"SQLite database not found: {source_path}",
                status_code=404,
            )

        self._settings.backup_dir.mkdir(parents=True, exist_ok=True)
        target_path = self._settings.backup_dir / self._build_backup_name()

        source = sqlite3.connect(str(source_path))
        target = sqlite3.connect(str(target_path))
        try:
            with target:
                source.backup(target)
        finally:
            target.close()
            source.close()

        backup = self._read_backup_file(target_path)
        logger.info(
            "SQLite backup created: {} ({} bytes)",
            target_path,
            backup.size_bytes,
        )
        return backup

    def list_sqlite_backups(self) -> DatabaseBackupListRead:
        backup_dir = self._settings.backup_dir
        backup_dir.mkdir(parents=True, exist_ok=True)
        backups = sorted(
            [self._read_backup_file(path) for path in backup_dir.glob("hap_*.db")],
            key=lambda item: item.created_at,
            reverse=True,
        )
        return DatabaseBackupListRead(
            items=backups,
            directory=str(backup_dir),
            database_engine="sqlite",
        )

    def _get_sqlite_database_path(self) -> Path:
        database_url = self._settings.database_url
        if not database_url.startswith("sqlite:///"):
            raise AppError(
                code=ErrorCode.validation_error,
                message="Database backup currently supports SQLite only.",
                status_code=400,
            )

        raw_path = database_url.replace("sqlite:///", "", 1)
        return Path(unquote(raw_path))

    @staticmethod
    def _build_backup_name() -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"hap_{timestamp}.db"

    @staticmethod
    def _read_backup_file(path: Path) -> DatabaseBackupRead:
        stat = path.stat()
        return DatabaseBackupRead(
            file_name=path.name,
            size_bytes=stat.st_size,
            created_at=datetime.fromtimestamp(stat.st_mtime),
        )
