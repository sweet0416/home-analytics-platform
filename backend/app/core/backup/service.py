import os
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote

from loguru import logger

from app.core.backup.repository import DatabaseRestoreRunRepository
from app.core.backup.schemas import DatabaseBackupListRead, DatabaseBackupRead, DatabaseRestoreRead
from app.core.config.settings import Settings
from app.core.database.session import SessionLocal, create_database_schema, engine
from app.shared.exceptions.base import AppError
from app.shared.exceptions.codes import ErrorCode


class DatabaseBackupService:
    RESTORE_CONFIRMATION = "RESTORE HAP DATABASE"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def create_sqlite_backup(self, label: str | None = None) -> DatabaseBackupRead:
        source_path = self._get_sqlite_database_path()
        if not source_path.exists():
            raise AppError(
                code=ErrorCode.not_found,
                message=f"SQLite database not found: {source_path}",
                status_code=404,
            )

        self._settings.backup_dir.mkdir(parents=True, exist_ok=True)
        target_path = self._settings.backup_dir / self._build_backup_name(label=label)

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
        self.prune_sqlite_backups()
        return backup

    def restore_sqlite_backup(self, file_name: str, confirmation: str) -> DatabaseRestoreRead:
        if confirmation != self.RESTORE_CONFIRMATION:
            raise AppError(
                code=ErrorCode.validation_error,
                message=f"Type '{self.RESTORE_CONFIRMATION}' to confirm database restore.",
                status_code=400,
            )

        restore_path = self.get_sqlite_backup_path(file_name)
        self._assert_sqlite_integrity(restore_path)
        safety_backup = self.create_sqlite_backup(label="pre_restore")
        database_path = self._get_sqlite_database_path()
        temp_restore_path = database_path.with_suffix(".restore.tmp")
        started_at = datetime.now()

        try:
            shutil.copy2(restore_path, temp_restore_path)
            self._assert_sqlite_integrity(temp_restore_path)
            engine.dispose()
            os.replace(temp_restore_path, database_path)
            create_database_schema()
        finally:
            temp_restore_path.unlink(missing_ok=True)

        logger.warning(
            "SQLite database restored from {} with safety backup {}",
            restore_path.name,
            safety_backup.file_name,
        )
        result = DatabaseRestoreRead(
            source_file_name=restore_path.name,
            safety_backup_file_name=safety_backup.file_name,
            status="success",
            message="Database restored successfully. Review application health after restore.",
            restored_at=started_at,
        )
        self._record_restore_result(result=result)
        return result

    def list_sqlite_backups(
        self,
        scheduler_status: dict[str, object] | None = None,
    ) -> DatabaseBackupListRead:
        backups = self._list_backup_files()
        return DatabaseBackupListRead(
            items=backups,
            directory=str(self._settings.backup_dir),
            database_engine="sqlite",
            retention_count=self._settings.backup_retention_count,
            total_size_bytes=sum(item.size_bytes for item in backups),
            scheduler=scheduler_status or {},
        )

    def prune_sqlite_backups(self) -> int:
        backups = self._list_backup_files()
        expired = backups[self._settings.backup_retention_count :]
        deleted_count = 0
        for backup in expired:
            path = self._settings.backup_dir / backup.file_name
            try:
                path.unlink(missing_ok=True)
                deleted_count += 1
                logger.info("Expired SQLite backup removed: {}", path)
            except OSError as exc:
                logger.warning("Failed to remove expired SQLite backup {}: {}", path, exc)
        return deleted_count

    def get_sqlite_backup_path(self, file_name: str) -> Path:
        if Path(file_name).name != file_name or not file_name.startswith("hap_"):
            raise AppError(
                code=ErrorCode.validation_error,
                message="Invalid backup file name.",
                status_code=400,
            )
        if not file_name.endswith(".db"):
            raise AppError(
                code=ErrorCode.validation_error,
                message="Only SQLite backup files can be downloaded.",
                status_code=400,
            )

        path = self._settings.backup_dir / file_name
        if not path.exists() or not path.is_file():
            raise AppError(
                code=ErrorCode.not_found,
                message=f"Backup file not found: {file_name}",
                status_code=404,
            )
        return path

    def _list_backup_files(self) -> list[DatabaseBackupRead]:
        backup_dir = self._settings.backup_dir
        backup_dir.mkdir(parents=True, exist_ok=True)
        return sorted(
            [self._read_backup_file(path) for path in backup_dir.glob("hap_*.db")],
            key=lambda item: item.created_at,
            reverse=True,
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
    def _assert_sqlite_integrity(path: Path) -> None:
        try:
            connection = sqlite3.connect(str(path))
            try:
                result = connection.execute("PRAGMA integrity_check").fetchone()
            finally:
                connection.close()
        except sqlite3.DatabaseError as exc:
            raise AppError(
                code=ErrorCode.validation_error,
                message=f"Invalid SQLite backup file: {path.name}",
                status_code=400,
            ) from exc

        if result is None or result[0] != "ok":
            raise AppError(
                code=ErrorCode.validation_error,
                message=f"SQLite integrity check failed for backup: {path.name}",
                status_code=400,
            )

    @staticmethod
    def _record_restore_result(result: DatabaseRestoreRead) -> None:
        db = SessionLocal()
        try:
            DatabaseRestoreRunRepository(db).record_run(
                source_file_name=result.source_file_name,
                safety_backup_file_name=result.safety_backup_file_name,
                confirmation="matched",
                status=result.status,
                message=result.message,
            )
        finally:
            db.close()

    @staticmethod
    def _build_backup_name(label: str | None = None) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        if label:
            normalized = "".join(char for char in label if char.isalnum() or char in {"_", "-"})
            return f"hap_{normalized}_{timestamp}.db"
        return f"hap_{timestamp}.db"

    @staticmethod
    def _read_backup_file(path: Path) -> DatabaseBackupRead:
        stat = path.stat()
        return DatabaseBackupRead(
            file_name=path.name,
            size_bytes=stat.st_size,
            created_at=datetime.fromtimestamp(stat.st_mtime),
        )
