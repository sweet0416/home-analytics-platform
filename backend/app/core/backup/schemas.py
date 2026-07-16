from datetime import datetime

from pydantic import BaseModel, Field


class DatabaseBackupRead(BaseModel):
    file_name: str
    size_bytes: int = Field(ge=0)
    created_at: datetime


class DatabaseRestoreRunRead(BaseModel):
    source_file_name: str
    safety_backup_file_name: str
    status: str
    message: str
    started_at: datetime
    finished_at: datetime | None
    created_at: datetime


class DatabaseBackupListRead(BaseModel):
    items: list[DatabaseBackupRead]
    directory: str
    database_engine: str
    retention_count: int = Field(ge=1)
    total_size_bytes: int = Field(ge=0)
    scheduler: dict[str, object]
    latest_restore: DatabaseRestoreRunRead | None = None
    restore_runs: list[DatabaseRestoreRunRead] = Field(default_factory=list)


class DatabaseRestoreRequest(BaseModel):
    file_name: str
    confirmation: str


class DatabaseRestoreRead(BaseModel):
    source_file_name: str
    safety_backup_file_name: str
    status: str
    message: str
    restored_at: datetime
