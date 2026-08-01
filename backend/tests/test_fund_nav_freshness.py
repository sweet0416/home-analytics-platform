from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.plugins.fund.application.services import FundService
from app.plugins.fund.domain.nav_freshness import count_business_days_since
from app.plugins.fund.infrastructure.persistence.repositories import FundRepository
from app.plugins.fund.interfaces.schemas import FundPositionCreate


class ProfileSourceStub:
    def __init__(self, fund_types: dict[str, str]) -> None:
        self.fund_types = fund_types

    def fetch_profile_type(self, fund_code: str) -> str:
        return self.fund_types[fund_code]


class FailingProfileSourceStub:
    def fetch_profile_type(self, fund_code: str) -> str:
        raise RuntimeError(f"Profile unavailable for {fund_code}")


def test_business_day_age_excludes_weekends() -> None:
    assert count_business_days_since(
        date(2026, 7, 31),
        date(2026, 8, 3),
    ) == 1
    assert count_business_days_since(
        date(2026, 7, 30),
        date(2026, 8, 3),
    ) == 2


def test_nav_freshness_summarizes_unique_position_funds(
    db_session: Session,
) -> None:
    repository = FundRepository(db_session)
    fund_cases = {
        "000001": (date(2026, 7, 31), "ETF"),
        "000002": (date(2026, 7, 29), "ETF"),
        "000003": (None, "ETF"),
        "000004": (date(2026, 7, 29), "ETF"),
    }
    for index, (fund_code, case) in enumerate(fund_cases.items(), start=1):
        nav_date, fund_type = case
        fund = repository.upsert_fund(
            code=fund_code,
            name=(
                "Fund 4 (QDII)"
                if fund_code == "000004"
                else f"Fund {index}"
            ),
            fund_type=fund_type,
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
        if nav_date is not None:
            repository.upsert_nav_record(
                fund=fund,
                nav_date=nav_date,
                unit_nav=Decimal("1"),
                accumulated_nav=Decimal("1"),
                source="test",
                note="",
            )
    repository.commit()

    result = FundService(repository).get_nav_freshness(
        stale_after_business_days=2,
        qdii_stale_after_business_days=4,
        as_of_date=date(2026, 8, 3),
    )

    assert result.position_count == 4
    assert result.fund_count == 4
    assert result.fresh_count == 2
    assert result.stale_count == 1
    assert result.missing_count == 1
    assert [item.status for item in result.items] == [
        "missing",
        "stale",
        "fresh",
        "fresh",
    ]
    qdii_item = next(item for item in result.items if item.fund_code == "000004")
    assert qdii_item.business_day_age == 3
    assert qdii_item.allowed_business_days == 4
    assert qdii_item.status == "fresh"


def test_profile_sync_normalizes_overseas_fund_type(
    db_session: Session,
) -> None:
    repository = FundRepository(db_session)
    for code, name in (
        ("050025", "S&P 500 Feeder A"),
        ("009776", "Domestic Fund A"),
    ):
        fund = repository.upsert_fund(
            code=code,
            name=name,
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

    source = ProfileSourceStub(
        {
            "050025": "指数型-海外股票",
            "009776": "混合型-偏股",
        }
    )
    result = FundService(repository, nav_source=source).sync_held_fund_profiles()

    assert result.total == 2
    assert result.updated == 1
    assert result.unchanged == 1
    assert result.failed == 0
    overseas = repository.get_fund_by_code("050025")
    domestic = repository.get_fund_by_code("009776")
    assert overseas is not None and overseas.fund_type == "QDII"
    assert domestic is not None and domestic.fund_type == "ETF"


def test_position_creation_automatically_normalizes_overseas_type(
    db_session: Session,
) -> None:
    repository = FundRepository(db_session)
    result = FundService(
        repository,
        nav_source=ProfileSourceStub(
            {"050025": "\u6307\u6570\u578b-\u6d77\u5916\u80a1\u7968"}
        ),
    ).create_position(
        FundPositionCreate(
            fund_code="050025",
            fund_name="S&P 500 Feeder A",
            fund_type="ETF",
            shares=Decimal("100"),
            cost_price=Decimal("1"),
        )
    )

    assert result.fund_type == "QDII"


def test_position_creation_retains_type_when_profile_lookup_fails(
    db_session: Session,
) -> None:
    result = FundService(
        FundRepository(db_session),
        nav_source=FailingProfileSourceStub(),
    ).create_position(
        FundPositionCreate(
            fund_code="009776",
            fund_name="Domestic Fund A",
            fund_type="mixed",
            shares=Decimal("100"),
            cost_price=Decimal("1"),
        )
    )

    assert result.fund_type == "mixed"
