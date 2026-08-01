from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from app.plugins.fund.application.services import FundService
from app.plugins.fund.infrastructure.persistence.repositories import FundRepository
from app.plugins.fund.infrastructure.sources.eastmoney import FundLatestNav


class LatestNavSourceStub:
    def __init__(self, nav_date: date) -> None:
        self.nav_date = nav_date

    def fetch_latest(self, fund_code: str, fund_type: str) -> FundLatestNav:
        return FundLatestNav(
            fund_code=fund_code,
            fund_name="Sample Fund",
            fund_type=fund_type,
            nav_date=self.nav_date,
            unit_nav=Decimal("1.1000"),
            accumulated_nav=Decimal("1.1000"),
            source="test",
            source_url="https://example.test/nav",
        )


def test_fund_nav_cron_runs_monday_through_friday() -> None:
    timezone = ZoneInfo("Asia/Shanghai")
    trigger = CronTrigger.from_crontab(
        "0 19-22 * * 0-4",
        timezone=timezone,
    )

    next_run = trigger.get_next_fire_time(
        None,
        datetime(2026, 7, 31, 22, 30, tzinfo=timezone),
    )

    assert next_run == datetime(2026, 8, 3, 19, 0, tzinfo=timezone)


def test_tracked_sync_does_not_treat_existing_latest_date_as_updated(
    db_session: Session,
) -> None:
    repository = FundRepository(db_session)
    fund = repository.upsert_fund(
        code="009777",
        name="Sample Fund",
        fund_type="mixed",
    )
    repository.create_position(
        fund=fund,
        account_name="Default",
        shares=Decimal("100"),
        cost_price=Decimal("1"),
        total_cost=Decimal("100"),
        current_nav=Decimal("1"),
        opened_at=None,
        tags="",
        note="",
    )
    for nav_date in (date(2026, 7, 28), date(2026, 7, 29)):
        repository.upsert_nav_record(
            fund=fund,
            nav_date=nav_date,
            unit_nav=Decimal("1.0000"),
            accumulated_nav=Decimal("1.0000"),
            source="test",
            note="",
        )
    repository.commit()

    unchanged = FundService(
        repository,
        nav_source=LatestNavSourceStub(date(2026, 7, 29)),
    ).sync_tracked_navs()
    advanced = FundService(
        repository,
        nav_source=LatestNavSourceStub(date(2026, 7, 30)),
    ).sync_tracked_navs()

    assert unchanged.updated == 0
    assert advanced.updated == 1
