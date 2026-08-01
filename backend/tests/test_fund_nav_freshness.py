from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.plugins.fund.application.services import FundService
from app.plugins.fund.domain.nav_freshness import count_business_days_since
from app.plugins.fund.infrastructure.persistence.repositories import FundRepository


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
    nav_dates = {
        "000001": date(2026, 7, 31),
        "000002": date(2026, 7, 29),
        "000003": None,
    }
    for index, (fund_code, nav_date) in enumerate(nav_dates.items(), start=1):
        fund = repository.upsert_fund(
            code=fund_code,
            name=f"Fund {index}",
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
        as_of_date=date(2026, 8, 3),
    )

    assert result.position_count == 3
    assert result.fund_count == 3
    assert result.fresh_count == 1
    assert result.stale_count == 1
    assert result.missing_count == 1
    assert [item.status for item in result.items] == [
        "missing",
        "stale",
        "fresh",
    ]
