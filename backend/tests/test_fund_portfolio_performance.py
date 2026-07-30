from datetime import date
from decimal import Decimal

from app.plugins.fund.domain.portfolio_performance import (
    PortfolioFundSeries,
    calculate_static_portfolio_performance,
)


def test_static_portfolio_uses_common_dates_and_normalized_weights() -> None:
    metrics = calculate_static_portfolio_performance(
        [
            PortfolioFundSeries(
                fund_code="A",
                weight=Decimal("0.75"),
                observations=[
                    (date(2026, 7, 1), Decimal("1")),
                    (date(2026, 7, 2), Decimal("1.1")),
                    (date(2026, 7, 3), Decimal("0.99")),
                ],
            ),
            PortfolioFundSeries(
                fund_code="B",
                weight=Decimal("0.25"),
                observations=[
                    (date(2026, 7, 1), Decimal("2")),
                    (date(2026, 7, 3), Decimal("2.2")),
                    (date(2026, 7, 4), Decimal("2.4")),
                ],
            ),
        ]
    )

    assert [point.nav_date for point in metrics.points] == [
        date(2026, 7, 1),
        date(2026, 7, 3),
    ]
    assert metrics.points[-1].portfolio_index == Decimal("101.750000")
    assert metrics.points[-1].equal_weight_index == Decimal("104.500000")
    assert metrics.risk.cumulative_return == Decimal("0.017500")
    assert metrics.equal_weight_return == Decimal("0.045000")


def test_static_portfolio_requires_two_common_dates() -> None:
    metrics = calculate_static_portfolio_performance(
        [
            PortfolioFundSeries(
                fund_code="A",
                weight=Decimal("1"),
                observations=[(date(2026, 7, 1), Decimal("1"))],
            )
        ]
    )

    assert metrics.points == []
    assert metrics.risk.cumulative_return is None
