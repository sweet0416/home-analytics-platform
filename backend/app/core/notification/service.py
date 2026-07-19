from datetime import datetime, timezone
from typing import Any, Literal

from loguru import logger
import requests
from sqlalchemy import desc, func, select

from app.core.config.settings import Settings
from app.core.database.session import SessionLocal
from app.core.notification.models import NotificationDeliveryRunModel
from app.core.notification.schemas import (
    NotificationChannel,
    NotificationChannelStatus,
    NotificationDeliveryRunPageRead,
    NotificationDeliveryRunRead,
    NotificationSendResult,
    NotificationStatusRead,
    NotificationTestResult,
)

NotificationResultStatus = Literal["sent", "skipped", "failed"]


class NotificationService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def get_status(self) -> NotificationStatusRead:
        return NotificationStatusRead(
            channels=[
                self._build_bark_status(),
                self._build_wecom_status(),
                self._build_whatsapp_status(),
                self._build_custom_webhook_status(),
            ],
            default_channel=NotificationChannel.all,
            note=(
                "iMessage \u6ca1\u6709\u5b98\u65b9 Linux/Docker \u670d\u52a1\u7aef\u53d1\u9001 API\uff1b"
                "\u5982\u9700 iMessage\uff0c\u8bf7\u901a\u8fc7 custom_webhook \u63a5\u5165 Mac "
                "\u6216 iPhone \u5feb\u6377\u6307\u4ee4\u6865\u63a5\u3002"
            ),
        )

    def send_test(
        self,
        channel: NotificationChannel,
        title: str,
        message: str,
        source: str = "manual_test",
    ) -> NotificationTestResult:
        channels = self._expand_channels(channel)
        results = [self._send_to_channel(item, title=title, message=message) for item in channels]
        self._record_results(source=source, title=title, message=message, results=results)
        return NotificationTestResult(requested_channel=channel, results=results)

    def list_delivery_runs(self, *, limit: int = 20) -> NotificationDeliveryRunPageRead:
        bounded_limit = max(1, min(limit, 100))
        db = SessionLocal()
        try:
            total = db.scalar(select(func.count()).select_from(NotificationDeliveryRunModel)) or 0
            rows = (
                db.scalars(
                    select(NotificationDeliveryRunModel)
                    .order_by(desc(NotificationDeliveryRunModel.created_at))
                    .limit(bounded_limit)
                )
                .all()
            )
            return NotificationDeliveryRunPageRead(
                items=[self._read_delivery_run(row) for row in rows],
                total=total,
                limit=bounded_limit,
            )
        finally:
            db.close()

    def _expand_channels(self, channel: NotificationChannel) -> list[NotificationChannel]:
        if channel == NotificationChannel.all:
            return [
                NotificationChannel.bark,
                NotificationChannel.wecom,
                NotificationChannel.whatsapp,
                NotificationChannel.custom_webhook,
            ]
        return [channel]

    def _send_to_channel(
        self,
        channel: NotificationChannel,
        title: str,
        message: str,
    ) -> NotificationSendResult:
        try:
            if channel == NotificationChannel.bark:
                return self._send_bark(title=title, message=message)
            if channel == NotificationChannel.wecom:
                return self._send_wecom(title=title, message=message)
            if channel == NotificationChannel.whatsapp:
                return self._send_whatsapp(title=title, message=message)
            if channel == NotificationChannel.custom_webhook:
                return self._send_custom_webhook(title=title, message=message)
            return self._skipped(channel, "Unsupported notification channel.")
        except requests.RequestException as exc:
            logger.exception("Notification send failed for {}: {}", channel, exc)
            return NotificationSendResult(channel=channel, status="failed", message=str(exc))
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unexpected notification failure for {}: {}", channel, exc)
            return NotificationSendResult(channel=channel, status="failed", message=str(exc))

    def _send_bark(self, title: str, message: str) -> NotificationSendResult:
        if not self._settings.notification_bark_enabled:
            return self._skipped(NotificationChannel.bark, "Bark is disabled.")
        server_url = self._settings.notification_bark_server_url.strip().rstrip("/")
        device_key = self._settings.notification_bark_device_key.strip()
        if not server_url or not device_key:
            return self._skipped(
                NotificationChannel.bark,
                "Bark server URL or device key is not configured.",
            )

        payload = {
            "title": title,
            "body": message,
            "group": self._settings.notification_bark_group.strip() or "HAP",
            "level": self._settings.notification_bark_level.strip() or "active",
        }
        sound = self._settings.notification_bark_sound.strip()
        if sound:
            payload["sound"] = sound

        response = requests.post(
            f"{server_url}/{device_key}",
            headers={"Content-Type": "application/json; charset=utf-8"},
            json=payload,
            timeout=self._settings.notification_timeout_seconds,
        )
        response.raise_for_status()
        response_payload = self._safe_json(response)
        code = response_payload.get("code")
        if code not in (None, 200):
            return NotificationSendResult(
                channel=NotificationChannel.bark,
                status="failed",
                message=str(response_payload.get("message") or response_payload),
            )
        return self._sent(NotificationChannel.bark, "Bark message sent.")

    def _send_wecom(self, title: str, message: str) -> NotificationSendResult:
        if not self._settings.notification_wecom_enabled:
            return self._skipped(NotificationChannel.wecom, "WeCom webhook is disabled.")
        webhook_url = self._settings.notification_wecom_webhook_url.strip()
        if not webhook_url:
            return self._skipped(NotificationChannel.wecom, "WeCom webhook URL is not configured.")

        response = requests.post(
            webhook_url,
            json={"msgtype": "markdown", "markdown": {"content": f"## {title}\n\n{message}"}},
            timeout=self._settings.notification_timeout_seconds,
        )
        response.raise_for_status()
        payload = self._safe_json(response)
        errcode = payload.get("errcode")
        if errcode not in (None, 0):
            return NotificationSendResult(
                channel=NotificationChannel.wecom,
                status="failed",
                message=str(payload.get("errmsg") or payload),
            )
        return self._sent(NotificationChannel.wecom, "WeCom message sent.")

    def _send_whatsapp(self, title: str, message: str) -> NotificationSendResult:
        if not self._settings.notification_whatsapp_enabled:
            return self._skipped(NotificationChannel.whatsapp, "WhatsApp Cloud API is disabled.")
        missing = [
            name
            for name, value in {
                "phone_number_id": self._settings.notification_whatsapp_phone_number_id,
                "access_token": self._settings.notification_whatsapp_access_token,
                "recipient_phone": self._settings.notification_whatsapp_recipient_phone,
            }.items()
            if not value.strip()
        ]
        if missing:
            return self._skipped(
                NotificationChannel.whatsapp,
                f"WhatsApp Cloud API is missing: {', '.join(missing)}.",
            )

        url = (
            "https://graph.facebook.com/"
            f"{self._settings.notification_whatsapp_graph_version.strip()}/"
            f"{self._settings.notification_whatsapp_phone_number_id.strip()}/messages"
        )
        response = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {self._settings.notification_whatsapp_access_token}",
                "Content-Type": "application/json",
            },
            json={
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": self._settings.notification_whatsapp_recipient_phone.strip(),
                "type": "text",
                "text": {"preview_url": False, "body": f"{title}\n\n{message}"},
            },
            timeout=self._settings.notification_timeout_seconds,
        )
        response.raise_for_status()
        payload = self._safe_json(response)
        return self._sent(
            NotificationChannel.whatsapp,
            "WhatsApp message sent.",
            provider_message_id=self._extract_whatsapp_message_id(payload),
        )

    def _send_custom_webhook(self, title: str, message: str) -> NotificationSendResult:
        if not self._settings.notification_custom_webhook_enabled:
            return self._skipped(NotificationChannel.custom_webhook, "Custom webhook is disabled.")
        webhook_url = self._settings.notification_custom_webhook_url.strip()
        if not webhook_url:
            return self._skipped(
                NotificationChannel.custom_webhook,
                "Custom webhook URL is not configured.",
            )

        headers = {"Content-Type": "application/json"}
        bearer_token = self._settings.notification_custom_webhook_bearer_token.strip()
        if bearer_token:
            headers["Authorization"] = f"Bearer {bearer_token}"

        response = requests.post(
            webhook_url,
            headers=headers,
            json={
                "source": "home-analytics-platform",
                "title": title,
                "message": message,
                "sent_at": datetime.now(timezone.utc).isoformat(),
            },
            timeout=self._settings.notification_timeout_seconds,
        )
        response.raise_for_status()
        return self._sent(NotificationChannel.custom_webhook, "Custom webhook message sent.")

    def _record_results(
        self,
        *,
        source: str,
        title: str,
        message: str,
        results: list[NotificationSendResult],
    ) -> None:
        db = SessionLocal()
        try:
            for result in results:
                db.add(
                    NotificationDeliveryRunModel(
                        source=self._truncate(source, 64),
                        channel=result.channel.value,
                        status=result.status,
                        title=self._truncate(title, 160),
                        message_preview=self._truncate(message, 500),
                        result_message=self._truncate(result.message, 1000),
                        provider_message_id=result.provider_message_id,
                        sent_at=result.sent_at.replace(tzinfo=None) if result.sent_at else None,
                    )
                )
            db.commit()
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            logger.exception("Failed to record notification delivery runs: {}", exc)
        finally:
            db.close()

    @staticmethod
    def _read_delivery_run(row: NotificationDeliveryRunModel) -> NotificationDeliveryRunRead:
        try:
            channel = NotificationChannel(row.channel)
        except ValueError:
            channel = NotificationChannel.custom_webhook
        status: NotificationResultStatus = (
            row.status if row.status in {"sent", "skipped", "failed"} else "failed"
        )
        return NotificationDeliveryRunRead(
            id=row.id,
            source=row.source,
            channel=channel,
            status=status,
            title=row.title,
            message_preview=row.message_preview,
            result_message=row.result_message,
            provider_message_id=row.provider_message_id,
            sent_at=row.sent_at,
            created_at=row.created_at,
        )

    def _build_bark_status(self) -> NotificationChannelStatus:
        server_url = self._settings.notification_bark_server_url.strip().rstrip("/")
        device_key = self._settings.notification_bark_device_key.strip()
        return NotificationChannelStatus(
            channel=NotificationChannel.bark,
            label="Bark iPhone \u63a8\u9001",
            enabled=self._settings.notification_bark_enabled,
            configured=bool(server_url and device_key),
            description=(
                "\u901a\u8fc7 Bark App \u7684\u8bbe\u5907 Key \u7ed9 iPhone "
                "\u63a8\u9001\u901a\u77e5\uff0c\u9002\u5408\u4e2a\u4eba\u5bb6\u5ead\u670d\u52a1\u5668\u3002"
            ),
            target=(
                f"{self._mask_url(server_url)}/{self._mask_key(device_key)}"
                if server_url
                else "\u672a\u914d\u7f6e"
            ),
        )

    def _build_wecom_status(self) -> NotificationChannelStatus:
        webhook_url = self._settings.notification_wecom_webhook_url.strip()
        return NotificationChannelStatus(
            channel=NotificationChannel.wecom,
            label="\u4f01\u4e1a\u5fae\u4fe1\u673a\u5668\u4eba",
            enabled=self._settings.notification_wecom_enabled,
            configured=bool(webhook_url),
            description="\u901a\u8fc7\u4f01\u4e1a\u5fae\u4fe1\u7fa4\u673a\u5668\u4eba Webhook \u63a8\u9001 Markdown \u6d88\u606f\u3002",
            target=self._mask_url(webhook_url),
        )

    def _build_whatsapp_status(self) -> NotificationChannelStatus:
        recipient = self._settings.notification_whatsapp_recipient_phone.strip()
        configured = all(
            [
                self._settings.notification_whatsapp_phone_number_id.strip(),
                self._settings.notification_whatsapp_access_token.strip(),
                recipient,
            ]
        )
        return NotificationChannelStatus(
            channel=NotificationChannel.whatsapp,
            label="WhatsApp Cloud API",
            enabled=self._settings.notification_whatsapp_enabled,
            configured=configured,
            description="\u901a\u8fc7 Meta WhatsApp Cloud API \u53d1\u9001\u6587\u672c\u6d88\u606f\u3002",
            target=self._mask_phone(recipient),
        )

    def _build_custom_webhook_status(self) -> NotificationChannelStatus:
        webhook_url = self._settings.notification_custom_webhook_url.strip()
        return NotificationChannelStatus(
            channel=NotificationChannel.custom_webhook,
            label="\u81ea\u5b9a\u4e49 Webhook / iMessage Bridge",
            enabled=self._settings.notification_custom_webhook_enabled,
            configured=bool(webhook_url),
            description=(
                "\u8c03\u7528\u81ea\u5b9a\u4e49 HTTP Webhook\uff0c\u53ef\u6865\u63a5 "
                "iMessage\u3001Bark\u3001Gotify\u3001ntfy \u7b49\u3002"
            ),
            target=self._mask_url(webhook_url),
        )

    @staticmethod
    def _sent(
        channel: NotificationChannel,
        message: str,
        provider_message_id: str | None = None,
    ) -> NotificationSendResult:
        return NotificationSendResult(
            channel=channel,
            status="sent",
            message=message,
            sent_at=datetime.now(timezone.utc),
            provider_message_id=provider_message_id,
        )

    @staticmethod
    def _skipped(channel: NotificationChannel, message: str) -> NotificationSendResult:
        return NotificationSendResult(channel=channel, status="skipped", message=message)

    @staticmethod
    def _safe_json(response: requests.Response) -> dict[str, Any]:
        try:
            payload = response.json()
        except ValueError:
            return {}
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _extract_whatsapp_message_id(payload: dict[str, Any]) -> str | None:
        messages = payload.get("messages")
        if not isinstance(messages, list) or not messages:
            return None
        first = messages[0]
        if not isinstance(first, dict):
            return None
        message_id = first.get("id")
        return str(message_id) if message_id else None

    @staticmethod
    def _mask_url(value: str) -> str:
        if not value:
            return "\u672a\u914d\u7f6e"
        if len(value) <= 28:
            return "***"
        return f"{value[:18]}...{value[-8:]}"

    @staticmethod
    def _mask_phone(value: str) -> str:
        if not value:
            return "\u672a\u914d\u7f6e"
        if len(value) <= 6:
            return "***"
        return f"{value[:3]}***{value[-3:]}"

    @staticmethod
    def _mask_key(value: str) -> str:
        if not value:
            return "\u672a\u914d\u7f6e"
        if len(value) <= 8:
            return "***"
        return f"{value[:4]}***{value[-4:]}"

    @staticmethod
    def _truncate(value: str, limit: int) -> str:
        if len(value) <= limit:
            return value
        return f"{value[: max(0, limit - 3)]}..."
