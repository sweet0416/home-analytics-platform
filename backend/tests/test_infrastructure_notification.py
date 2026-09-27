"""Synthetic health, isolated SQLite and fake transport only; no outbound requests."""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest
import requests
from loguru import logger
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.core.config.settings import Settings
from app.core.infrastructure_health import scheduler
from app.core.infrastructure_health.schemas import (
    InfrastructureHealthRead,
    InfrastructureNotificationState,
)
from app.core.notification import service as notification
from app.core.notification.models import NotificationDeliveryRunModel as Delivery
from app.core.notification.schemas import NotificationChannel as Channel
from app.core.notification.schemas import NotificationSendResult
from app.core.notification.service import NotificationService


def health(*, count=0, docker=True, pve=True, configured=True, minute=0):
    return InfrastructureHealthRead(
        checked_at=datetime(2026, 1, 1, tzinfo=UTC) + timedelta(minutes=minute),
        healthy=not configured or (count == 0 and docker and pve),
        configured_components=2 if configured else 0,
        reachable_components=int(docker) + int(pve) if configured else 0,
        alerts=[] if not configured or (count == 0 and docker and pve) else ["synthetic alert"],
        docker=dict(plugin="docker", version="test", enabled=configured, configured=configured,
                    reachable=docker, problematic=count, running=2, containers=3),
        pve=dict(plugin="pve", version="test", enabled=configured, configured=configured,
                 reachable=pve),
    )


def state(**kwargs):
    return InfrastructureNotificationState.from_health(health(**kwargs))


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    def forbidden(*args, **kwargs):
        raise AssertionError("Outbound network is forbidden")

    monkeypatch.setattr(requests.sessions.Session, "request", forbidden)
    engine = create_engine(f"sqlite:///{tmp_path / 'notifications.db'}")
    Delivery.__table__.create(engine)
    sessions = sessionmaker(bind=engine)
    monkeypatch.setattr(notification, "SessionLocal", sessions)
    # model_construct deliberately bypasses all Settings env/dotenv sources.
    settings = Settings.model_construct(
        notification_bark_enabled=True,
        notification_bark_server_url="https://synthetic.invalid",
        notification_bark_device_key="synthetic-key",
        infrastructure_health_notify_channel="bark",
    )
    service = NotificationService(settings)
    sender = Mock(side_effect=lambda **kw: service._sent(Channel.bark, "synthetic success"))
    monkeypatch.setattr(service, "_send_bark", sender)
    records = []
    sink = logger.add(lambda msg: records.append(msg.record.copy()), level="DEBUG")
    try:
        yield service, sender, sessions, settings, records
    finally:
        logger.remove(sink)
        engine.dispose()


def send(service, value, message="synthetic copy", channel=Channel.bark, source="infrastructure_health"):
    return service.send_health_change(
        channel=channel, title="synthetic title", message=message, state=value, source=source,
    ).results


def rows(sessions):
    with sessions() as db:
        return list(db.scalars(select(Delivery).order_by(Delivery.id)))


def test_first_healthy_is_suppressed(isolated):
    service, sender, sessions, *_ = isolated
    assert send(service, state())[0].message == "ALREADY_NORMAL"
    sender.assert_not_called()
    assert rows(sessions)[0].status == "skipped"


def test_scheduler_timeline_and_restart(isolated, monkeypatch):
    service, sender, sessions, settings, records = isolated
    monkeypatch.setattr(scheduler, "get_settings", lambda: settings)
    # New service instance for each check emulates process-local state loss.
    def factory(**kwargs):
        instance = NotificationService(**kwargs)
        monkeypatch.setattr(instance, "_send_bark", sender)
        return instance

    monkeypatch.setattr(scheduler, "NotificationService", factory)
    snapshots = iter([health(count=1, minute=0), health(count=1, minute=5),
                      health(count=1, minute=10), health(count=2, minute=15),
                      health(minute=20), health(minute=25)])
    monkeypatch.setattr(scheduler.InfrastructureHealthService, "check", lambda self: next(snapshots))
    for _ in range(6):
        scheduler._run_scheduled_health_check()
    assert [row.status for row in rows(sessions)] == ["sent", "skipped", "skipped", "sent", "sent", "skipped"]
    assert sender.call_count == 3
    assert [r["extra"]["decision"] for r in records if "decision" in r["extra"]] == [
        "FIRST_ALERT", "DUPLICATE", "DUPLICATE", "STATE_CHANGED", "RECOVERY", "ALREADY_NORMAL",
    ]


@pytest.mark.parametrize("change", ["wording", "long_message", "order", "timestamp", "metrics", "errors"])
def test_cosmetic_changes_do_not_send(isolated, change):
    service, sender, *_ = isolated
    first = health(count=2)
    first.alerts = ["alert A", "alert B"]
    second = first.model_copy(deep=True)
    first_message = "x" * 900 if change == "long_message" else "状态：异常\nold copy"
    second_message = "completely rewritten copy" if change == "wording" else first_message
    if change == "order":
        second.alerts.reverse()
    if change == "timestamp":
        second.checked_at += timedelta(minutes=5)
    if change == "metrics":
        second.docker.running = 50
        second.docker.containers = 52
        second.docker.docker_version = "different cosmetic version"
    if change == "errors":
        second.docker.error = "new display detail"
    assert send(service, InfrastructureNotificationState.from_health(first), first_message)[0].status == "sent"
    assert send(service, InfrastructureNotificationState.from_health(second), second_message)[0].message == "DUPLICATE"
    assert sender.call_count == 1


@pytest.mark.parametrize("changed", [dict(count=2), dict(count=1, docker=False), dict(count=1, pve=False)])
def test_meaningful_change_sends_update(isolated, changed):
    service, sender, *_ = isolated
    send(service, state(count=1))
    assert send(service, state(**changed))[0].status == "sent"
    assert sender.call_count == 2


def test_recovery_does_not_need_chinese_or_abnormal_copy(isolated):
    service, sender, *_ = isolated
    send(service, state(count=1), "all wording is arbitrary")
    assert send(service, state(), "recovered")[0].status == "sent"
    assert send(service, state(), "different recovery copy")[0].status == "skipped"
    assert sender.call_count == 2


@pytest.mark.parametrize("recovery", [False, True])
def test_failure_does_not_advance_successful_baseline(isolated, recovery):
    service, sender, sessions, *_ = isolated
    if recovery:
        send(service, state(count=1))
    target = state() if recovery else state(count=1)
    sender.side_effect = lambda **kw: NotificationSendResult(channel=Channel.bark, status="failed", message="synthetic failure")
    assert send(service, target)[0].status == "failed"
    sender.side_effect = lambda **kw: service._sent(Channel.bark, "synthetic success")
    assert send(service, target)[0].status == "sent"
    assert send(service, target)[0].status == "skipped"
    assert rows(sessions)[-2].status == "sent"


def test_failed_first_alert_then_normal_has_no_recovery(isolated):
    service, sender, *_ = isolated
    sender.side_effect = lambda **kw: NotificationSendResult(channel=Channel.bark, status="failed", message="synthetic failure")
    send(service, state(count=1))
    assert send(service, state())[0].message == "ALREADY_NORMAL"
    assert sender.call_count == 1


@pytest.mark.parametrize("legacy", [None, "invalid json", '{"version":99}', '{}'])
@pytest.mark.parametrize("current_abnormal", [False, True])
def test_legacy_unknown_history_never_parses_prose(isolated, legacy, current_abnormal):
    service, sender, sessions, *_ = isolated
    with sessions() as db:
        db.add(Delivery(source="infrastructure_health", channel="bark", status="sent",
                        title="legacy", message_preview="状态：异常", health_state=legacy))
        db.commit()
    target = state(count=1 if current_abnormal else 0)
    assert send(service, target)[0].status == ("sent" if current_abnormal else "skipped")
    assert send(service, target)[0].status == "skipped"
    assert sender.call_count == int(current_abnormal)


@pytest.mark.parametrize("enabled,configured,reason", [
    (False, True, "CHANNEL_DISABLED"), (True, False, "CHANNEL_UNAVAILABLE"),
])
def test_channel_cannot_advance_baseline_when_disabled_or_unavailable(isolated, enabled, configured, reason):
    service, sender, _, settings, _ = isolated
    settings.notification_bark_enabled = enabled
    settings.notification_bark_device_key = "synthetic-key" if configured else ""
    assert send(service, state(count=1))[0].message == reason
    sender.assert_not_called()
    settings.notification_bark_enabled = True
    settings.notification_bark_device_key = "synthetic-key"
    assert send(service, state(count=1))[0].status == "sent"


def test_per_channel_and_source_success_is_independent(isolated, monkeypatch):
    service, sender, _, settings, _ = isolated
    settings.notification_wecom_enabled = True
    settings.notification_wecom_webhook_url = "https://synthetic.invalid"
    wecom = Mock(return_value=NotificationSendResult(channel=Channel.wecom, status="failed", message="synthetic"))
    monkeypatch.setattr(service, "_send_wecom", wecom)
    send(service, state(count=1), channel=Channel.all)
    wecom.return_value = service._sent(Channel.wecom, "synthetic success")
    result = send(service, state(count=1), channel=Channel.all)
    assert [item.status for item in result] == ["skipped", "sent", "skipped", "skipped"]
    assert sender.call_count == 1
    assert wecom.call_count == 2
    assert send(service, state(count=1), source="other_synthetic_source")[0].status == "sent"


def test_transport_error_does_not_leak_url_or_secret(isolated):
    service, sender, sessions, _, records = isolated
    sentinel = "synthetic-private-sentinel"
    sender.side_effect = requests.RequestException(f"https://synthetic.invalid/{sentinel}")
    result = send(service, state(count=1))[0]
    assert result.status == "failed"
    assert result.message == "TRANSPORT_ERROR"
    assert sentinel not in repr(records)
    assert sentinel not in repr([row.result_message for row in rows(sessions)])
    assert any(r["extra"].get("outcome") == "DELIVERY_FAILED" for r in records)


def test_history_failure_is_distinct_from_delivery(isolated, monkeypatch):
    service, sender, sessions, _, records = isolated
    session_type = sessions.class_
    original = session_type.commit
    monkeypatch.setattr(session_type, "commit", Mock(side_effect=RuntimeError("synthetic DB failure")))
    assert send(service, state(count=1))[0].status == "sent"
    assert rows(sessions) == []
    assert any(r["extra"].get("reason") == "HISTORY_PERSIST_FAILED" for r in records)
    monkeypatch.setattr(session_type, "commit", original)
    assert send(service, state(count=1))[0].status == "sent"
    assert send(service, state(count=1))[0].status == "skipped"
    assert sender.call_count == 2


def test_latest_success_tie_breaks_by_id_not_old_history(isolated):
    service, _, sessions, *_ = isolated
    with sessions() as db:
        for value in [state(count=1), state()]:
            db.add(Delivery(source="infrastructure_health", channel="bark", status="sent", title="synthetic",
                            health_state=value.model_dump_json(), created_at=datetime(2026, 1, 1)))
        db.commit()
    assert send(service, state())[0].message == "ALREADY_NORMAL"


def test_manual_notification_remains_independent(isolated):
    service, sender, sessions, *_ = isolated
    service.send_test(Channel.bark, "test", "test")
    service.send_test(Channel.bark, "test", "test")
    assert sender.call_count == 2
    assert all(row.health_state is None for row in rows(sessions))


def test_unconfigured_health_does_not_create_condition_or_send(isolated, monkeypatch):
    service, sender, _, settings, _ = isolated
    unconfigured = health(count=99, docker=False, pve=False, configured=False)
    assert InfrastructureNotificationState.from_health(unconfigured).healthy
    monkeypatch.setattr(scheduler, "get_settings", lambda: settings)
    monkeypatch.setattr(scheduler.InfrastructureHealthService, "check", lambda self: unconfigured)
    factory = Mock(return_value=service)
    monkeypatch.setattr(scheduler, "NotificationService", factory)
    scheduler._run_scheduled_health_check()
    factory.assert_not_called()
    sender.assert_not_called()


def test_existing_scheduler_frequency_and_overlap_guard(isolated, monkeypatch):
    *_, settings, _ = isolated
    settings.infrastructure_health_notify_enabled = True
    fake_scheduler = Mock()
    monkeypatch.setattr(scheduler, "_scheduler", None)
    monkeypatch.setattr(scheduler, "BackgroundScheduler", Mock(return_value=fake_scheduler))
    monkeypatch.setattr(scheduler, "get_settings", lambda: settings)
    scheduler.start_infrastructure_health_scheduler()
    args, kwargs = fake_scheduler.add_job.call_args
    assert str(args[1]) == "cron[month='*', day='*', day_of_week='*', hour='*', minute='*/5']"
    assert kwargs["max_instances"] == 1
    assert kwargs["coalesce"] is True
