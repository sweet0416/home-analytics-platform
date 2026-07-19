from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class NotificationChannel(StrEnum):
    all = "all"
    wecom = "wecom"
    whatsapp = "whatsapp"
    custom_webhook = "custom_webhook"


class NotificationChannelStatus(BaseModel):
    channel: NotificationChannel
    label: str
    enabled: bool
    configured: bool
    description: str
    target: str


class NotificationStatusRead(BaseModel):
    channels: list[NotificationChannelStatus]
    default_channel: NotificationChannel
    supports_imessage_bridge: bool = True
    note: str


class NotificationTestRequest(BaseModel):
    channel: NotificationChannel = NotificationChannel.all
    title: str = Field(default="HAP 通知测试", min_length=1, max_length=120)
    message: str = Field(
        default="如果你收到这条消息，说明 Home Analytics Platform 推送通道已经连通。",
        min_length=1,
        max_length=2048,
    )


class NotificationSendResult(BaseModel):
    channel: NotificationChannel
    status: Literal["sent", "skipped", "failed"]
    message: str
    sent_at: datetime | None = None
    provider_message_id: str | None = None


class NotificationTestResult(BaseModel):
    requested_channel: NotificationChannel
    results: list[NotificationSendResult]
