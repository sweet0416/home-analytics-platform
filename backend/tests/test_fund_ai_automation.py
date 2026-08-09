from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from app.plugins.fund.domain.ai_automation import build_nav_fingerprint
from app.plugins.fund.infrastructure.persistence.models import FundAiAutomationRunModel
from app.plugins.fund.jobs import scheduler


class NavItem:
    def __init__(self, code: str, nav_date: date | None, value: str, status: str) -> None:
        self.fund_code = code
        self.nav_date = nav_date
        self.unit_nav = Decimal(value)
        self.status = status


def test_nav_fingerprint_is_order_independent() -> None:
    first = [
        NavItem("000002", date(2026, 8, 7), "1.2", "succeeded"),
        NavItem("000001", date(2026, 8, 7), "0.8", "succeeded"),
    ]
    second = list(reversed(first))

    assert build_nav_fingerprint(first) == build_nav_fingerprint(second)


def test_nav_fingerprint_ignores_failed_items() -> None:
    latest_date, fingerprint = build_nav_fingerprint(
        [
            NavItem("000001", date(2026, 8, 7), "0.8", "succeeded"),
            NavItem("000002", date(2026, 8, 7), "1.2", "failed"),
        ]
    )

    assert latest_date == date(2026, 8, 7)
    assert len(fingerprint) == 64


def test_automation_run_has_separate_ai_and_push_statuses() -> None:
    run = FundAiAutomationRunModel(
        scope_key="portfolio",
        report_date=date(2026, 8, 8),
        nav_fingerprint="fingerprint",
        summary_version="v1",
        model_name="deepseek-chat",
        prompt_version="v1",
        ai_status="PENDING",
        push_status="NOT_REQUESTED",
    )

    assert run.ai_status != run.push_status
    assert run.attempts is None


def _push_context() -> tuple[
    SimpleNamespace,
    SimpleNamespace,
    SimpleNamespace,
    SimpleNamespace,
    SimpleNamespace,
]:
    repository = SimpleNamespace(commit=lambda: None)
    service = SimpleNamespace(
        get_daily_ai_summary=lambda _snapshot_id: SimpleNamespace(summary="摘要"),
        get_daily_report_insights=lambda: [],
    )
    settings = SimpleNamespace(
        fund_nav_notify_enabled=True,
        notification_bark_enabled=True,
    )
    report = SimpleNamespace(report_date=date(2026, 8, 9))
    snapshot = SimpleNamespace(id=1, report_date=date(2026, 8, 9))
    return repository, service, settings, report, snapshot


def test_automatic_push_can_be_skipped_without_changing_ai_status() -> None:
    repository, service, settings, report, snapshot = _push_context()
    settings.notification_bark_enabled = False
    run = SimpleNamespace(
        ai_status="SUCCESS",
        push_status="NOT_REQUESTED",
        push_error_message="",
    )

    result = scheduler._push_automatic_ai_summary(
        repository=repository,
        service=service,
        settings=settings,
        report=report,
        snapshot=snapshot,
        run=run,
    )

    assert result == "success, push skipped"
    assert run.ai_status == "SUCCESS"
    assert run.push_status == "SKIPPED"


def test_automatic_push_failure_keeps_ai_success(monkeypatch) -> None:
    repository, service, settings, report, snapshot = _push_context()
    run = SimpleNamespace(
        ai_status="SUCCESS",
        push_status="NOT_REQUESTED",
        push_error_message="",
    )

    class FailedNotification:
        def __init__(self, *, settings):
            self.settings = settings

        def send(self, **_kwargs):
            return SimpleNamespace(
                results=[SimpleNamespace(status="failed", message="Bark unavailable")]
            )

    monkeypatch.setattr(scheduler, "FundDailyNotificationService", FailedNotification)

    result = scheduler._push_automatic_ai_summary(
        repository=repository,
        service=service,
        settings=settings,
        report=report,
        snapshot=snapshot,
        run=run,
    )

    assert result == "success, push failed"
    assert run.ai_status == "SUCCESS"
    assert run.push_status == "FAILED"
    assert "Bark unavailable" in run.push_error_message
