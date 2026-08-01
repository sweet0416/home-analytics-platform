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


class ProfileAwareLatestNavSourceStub(LatestNavSourceStub):
    def __init__(self, nav_date: date) -> None:
        super().__init__(nav_date)
        self.requested_types: list[str] = []

    def fetch_profile_type(self, fund_code: str) -> str:
        return "QDII - Equity"

    def fetch_latest(self, fund_code: str, fund_type: str) -> FundLatestNav:
        self.requested_types.append(fund_type)
        return super().fetch_latest(fund_code, fund_type)


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


def test_tracked_sync_persists_automatically_detected_fund_type(
    db_session: Session,
) -> None:
    repository = FundRepository(db_session)
    fund = repository.upsert_fund(
        code="050025",
        name="S&P 500 Feeder A",
        fund_type="ETF",
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
    repository.commit()
    source = ProfileAwareLatestNavSourceStub(date(2026, 7, 30))

    result = FundService(repository, nav_source=source).sync_tracked_navs()

    synced_fund = repository.get_fund_by_code("050025")
    assert result.succeeded == 1
    assert source.requested_types == ["QDII"]
    assert synced_fund is not None and synced_fund.fund_type == "QDII"
