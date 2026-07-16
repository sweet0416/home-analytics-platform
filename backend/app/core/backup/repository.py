from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.backup.models import DatabaseBackupRunModel, DatabaseRestoreRunModel
from app.core.backup.remote import RemoteBackupResult
from app.core.backup.schemas import DatabaseBackupRead


class DatabaseBackupRunRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def record_run(
        self,
        backup: DatabaseBackupRead,
        trigger_type: str,
        remote_result: RemoteBackupResult,
    ) -> DatabaseBackupRunModel:
        model = DatabaseBackupRunModel(
            trigger_type=trigger_type,
            local_file_name=backup.file_name,
            local_size_bytes=backup.size_bytes,
            local_created_at=backup.created_at,
            remote_enabled=remote_result.enabled,
            remote_configured=remote_result.configured,
            remote_status=remote_result.status,
            remote_message=remote_result.message,
            remote_asset_name=remote_result.asset_name,
            remote_uploaded_at=remote_result.uploaded_at,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return model

    def get_latest_remote_run(self) -> DatabaseBackupRunModel | None:
        statement = (
            select(DatabaseBackupRunModel)
            .where(DatabaseBackupRunModel.remote_enabled.is_(True))
            .order_by(DatabaseBackupRunModel.created_at.desc())
            .limit(1)
        )
        return self._db.execute(statement).scalar_one_or_none()


class DatabaseRestoreRunRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def record_run(
        self,
        source_file_name: str,
        safety_backup_file_name: str,
        confirmation: str,
        status: str,
        message: str,
    ) -> DatabaseRestoreRunModel:
        model = DatabaseRestoreRunModel(
            source_file_name=source_file_name,
            safety_backup_file_name=safety_backup_file_name,
            confirmation=confirmation,
            status=status,
            message=message,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return model
