from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class NotificationChannel(StrEnum):
    all = "all"
    bark = "bark"
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
    title: str = Field(default="HAP \u901a\u77e5\u6d4b\u8bd5", min_length=1, max_length=120)
    message: str = Field(
        default=(
            "\u5982\u679c\u4f60\u6536\u5230\u8fd9\u6761\u6d88\u606f\uff0c"
            "\u8bf4\u660e Home Analytics Platform \u63a8\u9001\u901a\u9053\u5df2\u7ecf\u8fde\u901a\u3002"
        ),
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


class NotificationDeliveryRunRead(BaseModel):
    id: int
    source: str
    channel: NotificationChannel
    status: Literal["sent", "skipped", "failed"]
    title: str
    message_preview: str
    result_message: str
    provider_message_id: str | None = None
    sent_at: datetime | None = None
    created_at: datetime


class NotificationDeliveryRunPageRead(BaseModel):
    items: list[NotificationDeliveryRunRead]
    total: int
    limit: int
