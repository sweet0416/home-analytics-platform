from datetime import date
from decimal import Decimal

from app.plugins.fund.domain.holding_correlation import (
    FundCorrelationSeries,
    calculate_holding_correlations,
)


def test_holding_correlation_uses_pairwise_common_return_dates() -> None:
    results = calculate_holding_correlations(
        [
            FundCorrelationSeries(
                fund_code="A",
                observations=[
                    (date(2026, 7, 1), Decimal("1")),
                    (date(2026, 7, 2), Decimal("2")),
                    (date(2026, 7, 3), Decimal("6")),
                ],
            ),
            FundCorrelationSeries(
                fund_code="B",
                observations=[
                    (date(2026, 7, 1), Decimal("2")),
                    (date(2026, 7, 2), Decimal("3")),
                    (date(2026, 7, 3), Decimal("6")),
                    (date(2026, 7, 4), Decimal("4")),
                ],
            ),
        ]
    )

    assert len(results) == 1
    assert results[0].observation_count == 2
    assert results[0].correlation == Decimal("1.000000")


def test_holding_correlation_returns_none_for_constant_series() -> None:
    results = calculate_holding_correlations(
        [
            FundCorrelationSeries(
                fund_code="A",
                observations=[
                    (date(2026, 7, 1), Decimal("1")),
                    (date(2026, 7, 2), Decimal("1")),
                    (date(2026, 7, 3), Decimal("1")),
                ],
            ),
            FundCorrelationSeries(
                fund_code="B",
                observations=[
                    (date(2026, 7, 1), Decimal("1")),
                    (date(2026, 7, 2), Decimal("2")),
                    (date(2026, 7, 3), Decimal("3")),
                ],
            ),
        ]
    )

    assert results[0].correlation is None
