from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database.base import Base


class DatabaseBackupRunModel(Base):
    __tablename__ = "database_backup_runs"
    __table_args__ = (
        Index("ix_database_backup_runs_created_at", "created_at"),
        Index("ix_database_backup_runs_remote_status", "remote_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trigger_type: Mapped[str] = mapped_column(String(32), default="manual")
    local_file_name: Mapped[str] = mapped_column(String(255), index=True)
    local_size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    local_created_at: Mapped[datetime] = mapped_column(DateTime)
    remote_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    remote_configured: Mapped[bool] = mapped_column(Boolean, default=False)
    remote_status: Mapped[str] = mapped_column(String(32), default="disabled")
    remote_message: Mapped[str] = mapped_column(Text, default="")
    remote_asset_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    remote_uploaded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
