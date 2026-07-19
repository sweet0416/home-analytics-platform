from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database.base import Base


class NotificationDeliveryRunModel(Base):
    __tablename__ = "notification_delivery_runs"
    __table_args__ = (
        Index("ix_notification_delivery_runs_created_at", "created_at"),
        Index("ix_notification_delivery_runs_channel_status", "channel", "status"),
        Index("ix_notification_delivery_runs_source", "source"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(64), default="manual_test")
    channel: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    title: Mapped[str] = mapped_column(String(160))
    message_preview: Mapped[str] = mapped_column(Text, default="")
    result_message: Mapped[str] = mapped_column(Text, default="")
    provider_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
