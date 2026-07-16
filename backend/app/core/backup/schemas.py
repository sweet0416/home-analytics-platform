from datetime import datetime

from pydantic import BaseModel, Field


class DatabaseBackupRead(BaseModel):
    file_name: str
    size_bytes: int = Field(ge=0)
    created_at: datetime


class DatabaseBackupListRead(BaseModel):
    items: list[DatabaseBackupRead]
    directory: str
    database_engine: str
    retention_count: int = Field(ge=1)
    total_size_bytes: int = Field(ge=0)
    scheduler: dict[str, object]
