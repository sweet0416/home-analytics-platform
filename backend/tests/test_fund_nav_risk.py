from datetime import date, timedelta
from decimal import Decimal

from app.plugins.fund.domain.nav_risk import calculate_nav_risk


def test_nav_risk_calculates_return_volatility_and_drawdown() -> None:
    start = date(2026, 1, 1)
    metrics = calculate_nav_risk(
        [
            (start, Decimal("1.00")),
            (start + timedelta(days=1), Decimal("1.10")),
            (start + timedelta(days=2), Decimal("0.88")),
            (start + timedelta(days=3), Decimal("0.99")),
        ]
    )

    assert metrics.sample_count == 4
    assert metrics.return_observation_count == 3
    assert metrics.cumulative_return == Decimal("-0.010000")
    assert metrics.maximum_drawdown == Decimal("-0.200000")
    assert metrics.drawdown_peak_date == start + timedelta(days=1)
    assert metrics.drawdown_trough_date == start + timedelta(days=2)
    assert metrics.positive_day_ratio == Decimal("0.666667")
    assert metrics.annualized_volatility is not None


def test_nav_risk_reports_insufficient_sample() -> None:
    sample_date = date(2026, 1, 1)

    metrics = calculate_nav_risk([(sample_date, Decimal("1.00"))])

    assert metrics.sample_count == 1
    assert metrics.cumulative_return is None
    assert metrics.maximum_drawdown is None
    assert metrics.annualized_volatility is None
