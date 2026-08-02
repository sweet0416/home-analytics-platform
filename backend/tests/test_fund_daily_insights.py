from datetime import date
from decimal import Decimal

from app.plugins.fund.domain.daily_insights import (
    DailyInsightSnapshot,
    calculate_daily_insights,
)


def _snapshot(
    report_date: date,
    *,
    current_value: str,
    return_rate: str,
    position_count: int = 4,
    hhi: str = "0.30",
    quality_level: str = "complete",
    nav_age_days: int = 1,
) -> DailyInsightSnapshot:
    return DailyInsightSnapshot(
        report_date=report_date,
        position_count=position_count,
        current_value=Decimal(current_value),
        unrealized_profit=Decimal(current_value) - Decimal("1000"),
        unrealized_return_rate=Decimal(return_rate),
        concentration_hhi=Decimal(hhi),
        quality_level=quality_level,
        nav_age_days=nav_age_days,
    )


def test_daily_insights_require_calendar_period_coverage() -> None:
    result = calculate_daily_insights(
        [
            _snapshot(date(2026, 8, 2), current_value="1100", return_rate="0.10"),
            _snapshot(date(2026, 7, 30), current_value="1000", return_rate="0"),
        ]
    )

    assert result.snapshot_count == 2
    assert all(item.status == "insufficient" for item in result.comparisons)
    assert result.comparisons[0].observed_span_days == 3
    assert "还需至少 4 天" in result.comparisons[0].explanation


def test_daily_insights_compare_with_latest_snapshot_not_after_target_date() -> None:
    result = calculate_daily_insights(
        [
            _snapshot(date(2026, 8, 2), current_value="1200", return_rate="0.20"),
            _snapshot(date(2026, 7, 27), current_value="1150", return_rate="0.15"),
            _snapshot(date(2026, 7, 25), current_value="1000", return_rate="0"),
            _snapshot(date(2026, 7, 1), current_value="900", return_rate="-0.10"),
        ]
    )

    seven_day, thirty_day = result.comparisons
    assert seven_day.status == "available"
    assert seven_day.baseline_date == date(2026, 7, 25)
    assert seven_day.current_value_change == Decimal("200")
    assert thirty_day.status == "available"
    assert thirty_day.baseline_date == date(2026, 7, 1)
    assert thirty_day.current_value_change == Decimal("300")


def test_daily_insights_flag_material_changes_and_quality_decline() -> None:
    result = calculate_daily_insights(
        [
            _snapshot(
                date(2026, 8, 2),
                current_value="1100",
                return_rate="0.08",
                position_count=5,
                hhi="0.38",
                quality_level="partial",
                nav_age_days=6,
            ),
            _snapshot(
                date(2026, 8, 1),
                current_value="1000",
                return_rate="0",
                hhi="0.30",
            ),
        ]
    )

    assert {alert.code for alert in result.alerts} == {
        "nav_stale",
        "data_quality_declined",
        "return_rate_large_change",
        "concentration_increased",
        "position_count_changed",
    }
