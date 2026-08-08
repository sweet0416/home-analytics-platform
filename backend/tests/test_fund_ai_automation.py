from datetime import date
from decimal import Decimal

from app.plugins.fund.domain.ai_automation import build_nav_fingerprint
from app.plugins.fund.infrastructure.persistence.models import FundAiAutomationRunModel


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
