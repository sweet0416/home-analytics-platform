from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Literal


@dataclass(frozen=True)
class DailyInsightSnapshot:
    report_date: date
    position_count: int
    current_value: Decimal | None
    unrealized_profit: Decimal | None
    unrealized_return_rate: Decimal | None
    concentration_hhi: Decimal | None
    quality_level: str
    nav_age_days: int | None


@dataclass(frozen=True)
class DailyPeriodComparison:
    period_days: int
    status: Literal["available", "insufficient"]
    latest_date: date | None
    baseline_date: date | None
    sample_count: int
    observed_span_days: int
    position_count_change: int | None
    current_value_change: Decimal | None
    unrealized_profit_change: Decimal | None
    unrealized_return_rate_change: Decimal | None
    concentration_hhi_change: Decimal | None
    explanation: str


@dataclass(frozen=True)
class DailyInsightAlert:
    code: str
    level: Literal["info", "warning"]
    message: str
    sample_scope: str


@dataclass(frozen=True)
class DailyInsights:
    snapshot_count: int
    latest_date: date | None
    comparisons: tuple[DailyPeriodComparison, ...]
    alerts: tuple[DailyInsightAlert, ...]


def calculate_daily_insights(
    snapshots: list[DailyInsightSnapshot],
    *,
    periods: tuple[int, ...] = (7, 30),
) -> DailyInsights:
    ordered = sorted(snapshots, key=lambda item: item.report_date, reverse=True)
    latest = ordered[0] if ordered else None
    comparisons = tuple(
        _build_period_comparison(ordered, period_days=period_days)
        for period_days in periods
    )
    alerts = _build_alerts(ordered)
    return DailyInsights(
        snapshot_count=len(ordered),
        latest_date=latest.report_date if latest else None,
        comparisons=comparisons,
        alerts=alerts,
    )


def _build_period_comparison(
    snapshots: list[DailyInsightSnapshot],
    *,
    period_days: int,
) -> DailyPeriodComparison:
    if not snapshots:
        return _insufficient_comparison(
            period_days=period_days,
            latest_date=None,
            sample_count=0,
            observed_span_days=0,
            explanation="还没有日报快照，暂时无法比较。",
        )

    latest = snapshots[0]
    observed_span_days = (latest.report_date - snapshots[-1].report_date).days
    target_date = latest.report_date - timedelta(days=period_days)
    baseline = next(
        (snapshot for snapshot in snapshots if snapshot.report_date <= target_date),
        None,
    )
    if baseline is None:
        remaining_days = max(period_days - observed_span_days, 1)
        return _insufficient_comparison(
            period_days=period_days,
            latest_date=latest.report_date,
            sample_count=len(snapshots),
            observed_span_days=observed_span_days,
            explanation=f"当前只覆盖 {observed_span_days} 天，还需至少 {remaining_days} 天形成基准。",
        )

    sample_count = sum(
        baseline.report_date <= snapshot.report_date <= latest.report_date
        for snapshot in snapshots
    )
    return DailyPeriodComparison(
        period_days=period_days,
        status="available",
        latest_date=latest.report_date,
        baseline_date=baseline.report_date,
        sample_count=sample_count,
        observed_span_days=(latest.report_date - baseline.report_date).days,
        position_count_change=latest.position_count - baseline.position_count,
        current_value_change=_optional_change(
            latest.current_value,
            baseline.current_value,
        ),
        unrealized_profit_change=_optional_change(
            latest.unrealized_profit,
            baseline.unrealized_profit,
        ),
        unrealized_return_rate_change=_optional_change(
            latest.unrealized_return_rate,
            baseline.unrealized_return_rate,
        ),
        concentration_hhi_change=_optional_change(
            latest.concentration_hhi,
            baseline.concentration_hhi,
        ),
        explanation=(
            f"比较 {baseline.report_date} 至 {latest.report_date}，"
            f"共使用 {sample_count} 条快照。"
        ),
    )


def _insufficient_comparison(
    *,
    period_days: int,
    latest_date: date | None,
    sample_count: int,
    observed_span_days: int,
    explanation: str,
) -> DailyPeriodComparison:
    return DailyPeriodComparison(
        period_days=period_days,
        status="insufficient",
        latest_date=latest_date,
        baseline_date=None,
        sample_count=sample_count,
        observed_span_days=observed_span_days,
        position_count_change=None,
        current_value_change=None,
        unrealized_profit_change=None,
        unrealized_return_rate_change=None,
        concentration_hhi_change=None,
        explanation=explanation,
    )


def _build_alerts(
    snapshots: list[DailyInsightSnapshot],
) -> tuple[DailyInsightAlert, ...]:
    if not snapshots:
        return ()
    latest = snapshots[0]
    alerts: list[DailyInsightAlert] = []
    if latest.nav_age_days is not None and latest.nav_age_days > 5:
        alerts.append(
            DailyInsightAlert(
                code="nav_stale",
                level="warning",
                message=f"最新净值已间隔 {latest.nav_age_days} 个自然日，请先确认数据是否更新。",
                sample_scope=f"快照日期 {latest.report_date}",
            )
        )
    if len(snapshots) < 2:
        return tuple(alerts)

    previous = snapshots[1]
    quality_rank = {"insufficient": 0, "partial": 1, "complete": 2}
    if quality_rank.get(latest.quality_level, 0) < quality_rank.get(
        previous.quality_level,
        0,
    ):
        alerts.append(
            DailyInsightAlert(
                code="data_quality_declined",
                level="warning",
                message="数据完整度较前次快照下降，请检查缺失净值或风险样本。",
                sample_scope=f"{previous.report_date} 至 {latest.report_date}",
            )
        )
    return_rate_change = _optional_change(
        latest.unrealized_return_rate,
        previous.unrealized_return_rate,
    )
    if return_rate_change is not None and abs(return_rate_change) >= Decimal("0.05"):
        alerts.append(
            DailyInsightAlert(
                code="return_rate_large_change",
                level="warning",
                message=(
                    "组合收益率较前次快照变化达到 "
                    f"{abs(return_rate_change) * 100:.2f} 个百分点，请核对净值和持仓变动。"
                ),
                sample_scope=f"{previous.report_date} 至 {latest.report_date}",
            )
        )
    concentration_change = _optional_change(
        latest.concentration_hhi,
        previous.concentration_hhi,
    )
    if concentration_change is not None and concentration_change >= Decimal("0.05"):
        alerts.append(
            DailyInsightAlert(
                code="concentration_increased",
                level="warning",
                message=f"持仓集中度 HHI 较前次快照上升 {concentration_change:.4f}。",
                sample_scope=f"{previous.report_date} 至 {latest.report_date}",
            )
        )
    position_change = latest.position_count - previous.position_count
    if position_change:
        alerts.append(
            DailyInsightAlert(
                code="position_count_changed",
                level="info",
                message=f"持仓记录数量较前次快照变化 {position_change:+d} 条。",
                sample_scope=f"{previous.report_date} 至 {latest.report_date}",
            )
        )
    return tuple(alerts)


def _optional_change(
    current: Decimal | None,
    baseline: Decimal | None,
) -> Decimal | None:
    if current is None or baseline is None:
        return None
    return current - baseline
