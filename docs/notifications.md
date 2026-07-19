# Notification Channels

HAP uses notification channels for lottery reminders, daily reports, backup failures, and future
HomeLab alerts. All credentials are read from backend environment variables only.

## Recommended Channels

### Bark iPhone Push

Bark is the recommended personal iPhone notification channel for HAP. Install the Bark app, copy
the device key shown in the app, and configure it in Portainer.

```text
NOTIFICATION_BARK_ENABLED=true
NOTIFICATION_BARK_SERVER_URL="https://api.day.app"
NOTIFICATION_BARK_DEVICE_KEY="your-bark-device-key"
NOTIFICATION_BARK_GROUP="HAP"
NOTIFICATION_BARK_SOUND=""
NOTIFICATION_BARK_LEVEL="active"
```

HAP sends a JSON request to the Bark endpoint with `title`, `body`, `group`, and optional sound
settings. For the public Bark service, keep `NOTIFICATION_BARK_SERVER_URL` as
`https://api.day.app`.

### WeCom Group Robot

Personal WeChat does not provide a normal official server-side push API for this use case, so HAP
uses WeCom group robot webhooks for the WeChat-family channel.

```text
NOTIFICATION_WECOM_ENABLED=true
NOTIFICATION_WECOM_WEBHOOK_URL="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=..."
```

The backend sends Markdown messages to the configured webhook.

### WhatsApp Cloud API

WhatsApp requires a Meta WhatsApp Cloud API app, a phone number id, an access token, and the
recipient phone number.

```text
NOTIFICATION_WHATSAPP_ENABLED=true
NOTIFICATION_WHATSAPP_GRAPH_VERSION="v20.0"
NOTIFICATION_WHATSAPP_PHONE_NUMBER_ID="..."
NOTIFICATION_WHATSAPP_ACCESS_TOKEN="..."
NOTIFICATION_WHATSAPP_RECIPIENT_PHONE="8613800000000"
```

The backend sends a text message through the Graph API messages endpoint.

### Custom Webhook / iMessage Bridge

iMessage has no official Linux or Docker server API. To use iMessage, bridge it through a Mac,
iPhone Shortcuts automation, Bark, Gotify, ntfy, or another HTTP service.

```text
NOTIFICATION_CUSTOM_WEBHOOK_ENABLED=true
NOTIFICATION_CUSTOM_WEBHOOK_URL="https://example.local/hap-notify"
NOTIFICATION_CUSTOM_WEBHOOK_BEARER_TOKEN=""
```

Payload:

```json
{
  "source": "home-analytics-platform",
  "title": "HAP 通知测试",
  "message": "如果你收到这条消息，说明 Home Analytics Platform 推送通道已经连通。",
  "sent_at": "2026-07-19T12:00:00+00:00"
}
```

## Test

Open `Settings -> 推送通知`, check whether Bark is enabled and configured, then click
`发送测试`.

API:

```bash
curl -X POST http://127.0.0.1:8088/api/v1/system/notifications/test \
  -H "Content-Type: application/json" \
  -d '{"channel":"all","title":"HAP 通知测试","message":"Hello from HAP"}'
```
