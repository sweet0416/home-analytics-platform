from datetime import date
from decimal import Decimal

from app.plugins.fund.domain.portfolio_benchmark import (
    calculate_portfolio_benchmark,
)


def test_benchmark_uses_only_common_dates_and_rebases_both_series() -> None:
    metrics = calculate_portfolio_benchmark(
        [
            (date(2026, 7, 1), Decimal("100")),
            (date(2026, 7, 2), Decimal("105")),
            (date(2026, 7, 3), Decimal("110")),
        ],
        [
            (date(2026, 6, 30), Decimal("90")),
            (date(2026, 7, 1), Decimal("100")),
            (date(2026, 7, 3), Decimal("105")),
        ],
    )

    assert [point.nav_date for point in metrics.points] == [
        date(2026, 7, 1),
        date(2026, 7, 3),
    ]
    assert metrics.points[0].portfolio_index == Decimal("100.000000")
    assert metrics.points[0].benchmark_index == Decimal("100.000000")
    assert metrics.portfolio_return == Decimal("0.100000")
    assert metrics.benchmark_return == Decimal("0.050000")
    assert metrics.relative_return == Decimal("0.047619")


def test_benchmark_requires_two_common_dates() -> None:
    metrics = calculate_portfolio_benchmark(
        [(date(2026, 7, 1), Decimal("100"))],
        [(date(2026, 7, 1), Decimal("1"))],
    )

    assert metrics.points == []
    assert metrics.relative_return is None
