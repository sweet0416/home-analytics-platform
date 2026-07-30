from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.plugins.fund.application.services import FundService
from app.plugins.fund.domain.lookthrough import (
    LookthroughFundDisclosure,
    LookthroughHolding,
    calculate_lookthrough,
)
from app.plugins.fund.infrastructure.persistence.repositories import (
    FundRepository,
)


def test_lookthrough_aggregates_duplicates_and_excludes_stale_data() -> None:
    metrics = calculate_lookthrough(
        [
            LookthroughFundDisclosure(
                fund_code="A",
                allocation_weight=Decimal("0.60"),
                report_date=date(2026, 6, 30),
                holdings=[
                    LookthroughHolding(
                        asset_code="X",
                        asset_name="Asset X",
                        nav_ratio=Decimal("0.10"),
                    ),
                ],
            ),
            LookthroughFundDisclosure(
                fund_code="B",
                allocation_weight=Decimal("0.25"),
                report_date=date(2026, 6, 30),
                holdings=[
                    LookthroughHolding(
                        asset_code="X",
                        asset_name="Asset X",
                        nav_ratio=Decimal("0.20"),
                    ),
                ],
            ),
            LookthroughFundDisclosure(
                fund_code="STALE",
                allocation_weight=Decimal("0.15"),
                report_date=date(2025, 1, 1),
                holdings=[
                    LookthroughHolding(
                        asset_code="Y",
                        asset_name="Asset Y",
                        nav_ratio=Decimal("0.50"),
                    ),
                ],
            ),
        ],
        as_of_date=date(2026, 7, 31),
        stale_after_days=180,
    )

    assert metrics.coverage_weight == Decimal("0.85000000")
    assert metrics.disclosed_weight == Decimal("0.11000000")
    assert metrics.assets[0].asset_code == "X"
    assert metrics.assets[0].fund_count == 2
    assert metrics.assets[0].portfolio_weight == Decimal("0.11000000")
    assert metrics.stale_fund_codes == ["STALE"]


def test_lookthrough_service_reads_persisted_disclosures(
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
    repository.upsert_disclosure(
        fund=fund,
        report_date=datetime.now(ZoneInfo("Asia/Shanghai")).date(),
        report_period="2026Q2",
        asset_type="stock",
        source="test",
        source_url="https://example.test",
        holdings=[
            (
                1,
                "stock",
                "300308",
                "中际旭创",
                Decimal("0.10"),
                None,
                None,
            )
        ],
    )
    repository.commit()
    repository.upsert_disclosure(
        fund=fund,
        report_date=datetime.now(ZoneInfo("Asia/Shanghai")).date(),
        report_period="2026Q2",
        asset_type="stock",
        source="test",
        source_url="https://example.test/updated",
        holdings=[
            (
                1,
                "stock",
                "300308",
                "中际旭创",
                Decimal("0.10"),
                None,
                None,
            )
        ],
    )
    repository.commit()

    result = FundService(repository).get_lookthrough()

    assert result.fund_count == 1
    assert result.current_disclosure_count == 1
    assert result.coverage_weight == Decimal("1.00000000")
    assert result.disclosed_weight == Decimal("0.10000000")
    assert result.assets[0].asset_code == "300308"
