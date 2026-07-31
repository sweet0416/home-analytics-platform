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
from app.plugins.fund.domain.target_links import TargetFundLink
from app.plugins.fund.infrastructure.persistence.repositories import (
    FundRepository,
)
from app.plugins.fund.infrastructure.sources.eastmoney_holdings import (
    FundDisclosureHolding,
    FundHoldingsDisclosure,
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
    assert result.snapshots[0].source_mode == "direct"
    assert result.snapshots[0].covered_weight == Decimal("1.00000000")


def test_lookthrough_uses_current_target_etf_when_direct_is_stale(
    db_session: Session,
) -> None:
    repository = FundRepository(db_session)
    parent = repository.upsert_fund(
        code="050025",
        name="Linked Fund",
        fund_type="QDII",
    )
    target = repository.upsert_fund(
        code="513500",
        name="Target ETF",
        fund_type="ETF",
    )
    repository.create_position(
        fund=parent,
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
        fund=parent,
        report_date=date(2025, 1, 1),
        report_period="2024Q4",
        asset_type="stock",
        source="test",
        source_url="https://example.test/parent",
        holdings=[
            (1, "stock", "OLD", "Old Asset", Decimal("0.50"), None, None)
        ],
    )
    today = datetime.now(ZoneInfo("Asia/Shanghai")).date()
    repository.upsert_disclosure(
        fund=target,
        report_date=today,
        report_period="2026Q2",
        asset_type="stock",
        source="test",
        source_url="https://example.test/target",
        holdings=[
            (1, "stock", "AAPL", "Apple", Decimal("0.10"), None, None)
        ],
    )
    repository.commit()

    result = FundService(
        repository,
        target_links=[
            TargetFundLink(
                parent_fund_code="050025",
                target_fund_code="513500",
                target_fund_name="Target ETF",
                target_allocation_ratio=Decimal("0.94"),
                report_date=today,
                source_url="https://example.test/relation",
            )
        ],
    ).get_lookthrough(stale_after_days=180)

    assert result.current_disclosure_count == 1
    assert result.coverage_weight == Decimal("0.94000000")
    assert result.disclosed_weight == Decimal("0.09400000")
    assert result.assets[0].asset_code == "AAPL"
    assert result.snapshots[0].source_mode == "target_etf"
    assert result.snapshots[0].target_fund_code == "513500"
    assert result.snapshots[0].covered_weight == Decimal("0.94000000")


def test_lookthrough_prefers_current_direct_disclosure(
    db_session: Session,
) -> None:
    repository = FundRepository(db_session)
    parent = repository.upsert_fund(
        code="PARENT",
        name="Parent",
        fund_type="QDII",
    )
    target = repository.upsert_fund(
        code="TARGET",
        name="Target ETF",
        fund_type="ETF",
    )
    repository.create_position(
        fund=parent,
        account_name="Default",
        shares=Decimal("100"),
        cost_price=Decimal("1"),
        total_cost=Decimal("100"),
        current_nav=Decimal("1"),
        opened_at=None,
        tags="",
        note="",
    )
    today = datetime.now(ZoneInfo("Asia/Shanghai")).date()
    for fund, code in ((parent, "DIRECT"), (target, "DERIVED")):
        repository.upsert_disclosure(
            fund=fund,
            report_date=today,
            report_period="2026Q2",
            asset_type="stock",
            source="test",
            source_url=f"https://example.test/{code.lower()}",
            holdings=[
                (1, "stock", code, code, Decimal("0.10"), None, None)
            ],
        )
    repository.commit()

    result = FundService(
        repository,
        target_links=[
            TargetFundLink(
                parent_fund_code="PARENT",
                target_fund_code="TARGET",
                target_fund_name="Target ETF",
                target_allocation_ratio=Decimal("0.90"),
                report_date=today,
                source_url="https://example.test/relation",
            )
        ],
    ).get_lookthrough(stale_after_days=180)

    assert result.coverage_weight == Decimal("1.00000000")
    assert result.assets[0].asset_code == "DIRECT"
    assert result.snapshots[0].source_mode == "direct"
    assert result.snapshots[0].target_fund_code is None


def test_disclosure_sync_includes_configured_target_etf(
    db_session: Session,
) -> None:
    repository = FundRepository(db_session)
    parent = repository.upsert_fund(
        code="050025",
        name="Linked Fund",
        fund_type="QDII",
    )
    repository.create_position(
        fund=parent,
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
    today = datetime.now(ZoneInfo("Asia/Shanghai")).date()

    class HoldingsSourceStub:
        def __init__(self) -> None:
            self.calls: list[str] = []

        def fetch_latest(self, fund_code: str) -> FundHoldingsDisclosure:
            self.calls.append(fund_code)
            return FundHoldingsDisclosure(
                fund_code=fund_code,
                fund_name=f"Fund {fund_code}",
                report_date=today,
                report_period="2026Q2",
                asset_type="stock",
                source="test",
                source_url=f"https://example.test/{fund_code}",
                holdings=[
                    FundDisclosureHolding(
                        rank=1,
                        asset_type="stock",
                        asset_code="AAPL",
                        asset_name="Apple",
                        nav_ratio=Decimal("0.10"),
                        reported_quantity=None,
                        reported_market_value=None,
                    )
                ],
            )

    source = HoldingsSourceStub()
    result = FundService(
        repository,
        holdings_source=source,
        target_links=[
            TargetFundLink(
                parent_fund_code="050025",
                target_fund_code="513500",
                target_fund_name="Target ETF",
                target_allocation_ratio=Decimal("0.94"),
                report_date=today,
                source_url="https://example.test/relation",
            )
        ],
    ).sync_holding_disclosures()

    assert result.total == 2
    assert result.succeeded == 2
    assert sorted(source.calls) == ["050025", "513500"]
    target = repository.get_fund_by_code("513500")
    assert target is not None
    disclosures = repository.list_latest_disclosures(fund_ids=[target.id])
    assert disclosures[0].holdings[0].asset_code == "AAPL"
