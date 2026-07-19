from datetime import datetime, timezone
from typing import Any

from loguru import logger
import requests

from app.core.config.settings import Settings
from app.core.notification.schemas import (
    NotificationChannel,
    NotificationChannelStatus,
    NotificationSendResult,
    NotificationStatusRead,
    NotificationTestResult,
)


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
                "iMessage 没有官方 Linux/Docker 服务端发送 API；如需 iMessage，"
                "请通过 custom_webhook 接入 Mac 或 iPhone 快捷指令桥接。"
            ),
        )

    def send_test(
        self,
        channel: NotificationChannel,
        title: str,
        message: str,
    ) -> NotificationTestResult:
        channels = self._expand_channels(channel)
        results = [self._send_to_channel(item, title=title, message=message) for item in channels]
        return NotificationTestResult(requested_channel=channel, results=results)

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
            return NotificationSendResult(
                channel=channel,
                status="failed",
                message=str(exc),
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unexpected notification failure for {}: {}", channel, exc)
            return NotificationSendResult(
                channel=channel,
                status="failed",
                message=str(exc),
            )

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

        content = f"## {title}\n\n{message}"
        response = requests.post(
            webhook_url,
            json={"msgtype": "markdown", "markdown": {"content": content}},
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
        message_id = self._extract_whatsapp_message_id(payload)
        return self._sent(
            NotificationChannel.whatsapp,
            "WhatsApp message sent.",
            provider_message_id=message_id,
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

    def _build_bark_status(self) -> NotificationChannelStatus:
        server_url = self._settings.notification_bark_server_url.strip().rstrip("/")
        device_key = self._settings.notification_bark_device_key.strip()
        return NotificationChannelStatus(
            channel=NotificationChannel.bark,
            label="Bark iPhone 推送",
            enabled=self._settings.notification_bark_enabled,
            configured=bool(server_url and device_key),
            description="通过 Bark App 的设备 Key 给 iPhone 推送通知，适合个人家庭服务器。",
            target=(
                f"{self._mask_url(server_url)}/{self._mask_key(device_key)}"
                if server_url
                else "未配置"
            ),
        )

    def _build_wecom_status(self) -> NotificationChannelStatus:
        webhook_url = self._settings.notification_wecom_webhook_url.strip()
        return NotificationChannelStatus(
            channel=NotificationChannel.wecom,
            label="企业微信机器人",
            enabled=self._settings.notification_wecom_enabled,
            configured=bool(webhook_url),
            description="通过企业微信群机器人 Webhook 推送 Markdown 消息。",
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
            description="通过 Meta WhatsApp Cloud API 发送文本消息。",
            target=self._mask_phone(recipient),
        )

    def _build_custom_webhook_status(self) -> NotificationChannelStatus:
        webhook_url = self._settings.notification_custom_webhook_url.strip()
        return NotificationChannelStatus(
            channel=NotificationChannel.custom_webhook,
            label="自定义 Webhook / iMessage Bridge",
            enabled=self._settings.notification_custom_webhook_enabled,
            configured=bool(webhook_url),
            description="调用自定义 HTTP Webhook，可桥接 iMessage、Bark、Gotify、ntfy 等。",
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
            return "未配置"
        if len(value) <= 28:
            return "***"
        return f"{value[:18]}...{value[-8:]}"

    @staticmethod
    def _mask_phone(value: str) -> str:
        if not value:
            return "未配置"
        if len(value) <= 6:
            return "***"
        return f"{value[:3]}***{value[-3:]}"

    @staticmethod
    def _mask_key(value: str) -> str:
        if not value:
            return "未配置"
        if len(value) <= 8:
            return "***"
        return f"{value[:4]}***{value[-4:]}"
