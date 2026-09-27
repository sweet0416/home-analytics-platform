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

## DLT Sync Notifications

DLT sync jobs can reuse the notification service.

```text
LOTTERY_DLT_NOTIFY_ENABLED=true
LOTTERY_DLT_NOTIFY_CHANNEL="all"
LOTTERY_DLT_NOTIFY_ON_NO_CHANGES=false
```

Default behavior:

- Send a notification when scheduled sync inserts a new DLT draw.
- Send a notification when manual sync finishes, including no-change runs.
- Send a notification when scheduled or manual sync fails.
- Do not send a notification when there is no new draw, unless
  `LOTTERY_DLT_NOTIFY_ON_NO_CHANGES=true`.
- Do not push one notification per backfilled history page. Backfill progress stays in the sync
  detail view to avoid noisy phone notifications.

For Bark-only notifications, set:

```text
LOTTERY_DLT_NOTIFY_CHANNEL="bark"
```

## Delivery History

Every channel-level delivery result is recorded in SQLite table
`notification_delivery_runs`.

Recorded fields include source, channel, status, title, message preview, provider result message,
provider message id, sent time, and created time. Secrets such as Bark device keys, Webhook URLs,
tokens, and phone numbers are never stored in this table.

API:

```bash
curl http://127.0.0.1:8088/api/v1/system/notifications/runs?limit=20
```

The Settings page shows the latest delivery records below the notification test form.

## Infrastructure Health Deduplication (candidate behavior)

This describes the repository candidate, not a production deployment or a live notification test.
The optional infrastructure scheduler defaults to `*/5 * * * *` in `Asia/Shanghai`, with one
instance per job and coalescing enabled. No configured infrastructure plugins means no delivery.
Docker monitoring remains host-wide, including stopped containers; classification and PVE
monitoring are unchanged. HAP API/database health is not added to this notification state.

### Flow and state

`InfrastructureHealthService.check()` obtains the existing Docker/PVE status. The scheduler
projects this into `InfrastructureNotificationState` and renders the notification separately.
`NotificationService.send_health_change()` decides per channel, sends through the existing
transport, and persists delivery history. Rendering still occurs before the call, but neither
title nor body participates in the decision.

The version-1 fingerprint is the canonical typed tuple of:

- configured Docker being unreachable;
- configured Docker's existing problematic-container count (zero if unconfigured);
- configured PVE being unreachable.

All clear means normal; any condition means abnormal. Equality compares these typed fields,
not a hash of the message or JSON key order. Check times, human-readable alerts and their order,
error wording, version labels, total/running container counts and message formatting are ignored.
The current status model has no abnormal-container identities: replacing an abnormal container
with another while preserving the count is not detectable. No extra Docker request or invented
container-set fingerprint is introduced.

### Decisions and delivery

The baseline is the latest **successfully delivered and persisted** record for the same source
and channel, ordered by creation time then row ID. Failed and skipped records never advance it.

| Previous successful state | Current state | Decision |
| --- | --- | --- |
| None / unknown / normal | Normal | No delivery (`ALREADY_NORMAL`) |
| None / unknown / normal | Abnormal | `FIRST_ALERT` |
| Abnormal A | Same abnormal A | Suppress (`DUPLICATE`) |
| Abnormal A | Different abnormal B | `STATE_CHANGED` |
| Abnormal | Normal | `RECOVERY` |

Disabled or unconfigured channels produce `CHANNEL_DISABLED` or `CHANNEL_UNAVAILABLE` without
sending. A failed alert or failed recovery remains eligible on the next scheduled check; there
is no immediate retry loop. A first alert that fails followed by normal health sends no recovery.
If an older abnormal alert succeeded and a later update failed, recovery still refers to that
older successful alert. Each channel is independent. Persisted history survives process restart.

Decision/outcome logs use fixed reason categories, not provider payloads or credential-bearing
URLs. Routine suppression is DEBUG; delivery is INFO; delivery failure is WARNING. A transport
exception returns `TRANSPORT_ERROR` or `PROVIDER_ERROR` rather than persisting its raw text.
`HISTORY_PERSIST_FAILED` distinguishes an uncommitted history write from transport delivery.
History recording remains best-effort: delivery success followed by a database failure or a
process crash can cause a later duplicate. This is **not** an exactly-once or multi-worker protocol.
Provider response bodies retain the existing result handling; this is not a general-purpose
sanitization overhaul of every external provider response.

### Schema and legacy records

Revision `20260927_1200` adds one nullable TEXT column, `notification_delivery_runs.health_state`,
containing the small versioned JSON state. Existing fields are delivery status, display text and
provider IDs, not metadata; overloading them would mix provider/copy semantics with canonical
state. No new table, dependency, UI/API field or notification setting is needed.

Old rows are left intact with NULL state. Missing, malformed or unknown-version state is treated
as an unknown baseline; old Chinese/English prose is never parsed. On upgrade, a currently
abnormal condition can send one fresh alert per channel and establish a baseline after success.
A currently normal condition stays silent, even if legacy prose described an abnormal alert:
an old-only recovery cannot be reconstructed safely. Repeated normal checks remain silent.
Delivery/persistence failures can still retry as described above, not silently mark an alert sent.

The candidate migration is tested on disposable SQLite databases, including retained legacy
history and repeated startup. It is not applied to production by this change. Existing startup
migration and restore-safety protocols remain unchanged. A later authorized deployment must run
the existing migrations before the new ORM code queries history; code rollback can leave the
nullable column in place. Do not downgrade or delete production notification history for rollback.

### Isolated validation

With the existing `backend/requirements-dev.txt` environment, the repository's isolated runner
can run the full suite without caller Settings or checkout dotenv:

```text
backend/.venv/Scripts/python.exe backend/scripts/check_sqlite_concurrency.py --full
```

The launcher name reflects its original SQLite task; `--full` runs all backend tests. The focused
cases are in `test_infrastructure_notification.py` and `test_notification_state_migration.py`.
They use disposable databases, synthetic settings, fake transports and a requests network deny
guard. Coverage includes copy/long-message changes, ordering/time changes, transitions, delivery
failures, mixed channel outcomes, legacy state, restart, history-write failure and schema upgrade.
