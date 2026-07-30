from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.plugins.fund.domain.nav_risk import (
    FundNavRiskMetrics,
    calculate_nav_risk,
)

INDEX_BASE = Decimal("100")
VALUE_PRECISION = Decimal("0.000001")


@dataclass(frozen=True)
class PortfolioFundSeries:
    fund_code: str
    weight: Decimal
    observations: list[tuple[date, Decimal]]


@dataclass(frozen=True)
class PortfolioPerformancePoint:
    nav_date: date
    portfolio_index: Decimal
    equal_weight_index: Decimal
    drawdown: Decimal


@dataclass(frozen=True)
class PortfolioPerformanceMetrics:
    points: list[PortfolioPerformancePoint]
    risk: FundNavRiskMetrics
    equal_weight_return: Decimal | None


def calculate_static_portfolio_performance(
    series: list[PortfolioFundSeries],
) -> PortfolioPerformanceMetrics:
    prepared = [
        (
            item,
            {
                nav_date: nav
                for nav_date, nav in item.observations
                if nav > 0
            },
        )
        for item in series
        if item.weight > 0
    ]
    if not prepared:
        return _empty_metrics()

    common_dates = set(prepared[0][1])
    for _, observations in prepared[1:]:
        common_dates.intersection_update(observations)
    ordered_dates = sorted(common_dates)
    if len(ordered_dates) < 2:
        return _empty_metrics()

    total_weight = sum((item.weight for item, _ in prepared), Decimal("0"))
    normalized_weights = [
        item.weight / total_weight for item, _ in prepared
    ]
    first_date = ordered_dates[0]
    baselines = [observations[first_date] for _, observations in prepared]
    peak = INDEX_BASE
    points: list[PortfolioPerformancePoint] = []

    for nav_date in ordered_dates:
        normalized_values = [
            observations[nav_date] / baseline
            for (_, observations), baseline in zip(
                prepared,
                baselines,
                strict=True,
            )
        ]
        portfolio_index = INDEX_BASE * sum(
            (
                weight * normalized
                for weight, normalized in zip(
                    normalized_weights,
                    normalized_values,
                    strict=True,
                )
            ),
            Decimal("0"),
        )
        equal_weight_index = (
            INDEX_BASE
            * sum(normalized_values, Decimal("0"))
            / Decimal(len(normalized_values))
        )
        peak = max(peak, portfolio_index)
        points.append(
            PortfolioPerformancePoint(
                nav_date=nav_date,
                portfolio_index=portfolio_index.quantize(VALUE_PRECISION),
                equal_weight_index=equal_weight_index.quantize(VALUE_PRECISION),
                drawdown=(portfolio_index / peak - Decimal("1")).quantize(
                    VALUE_PRECISION
                ),
            )
        )

    risk = calculate_nav_risk(
        [(point.nav_date, point.portfolio_index) for point in points]
    )
    equal_weight_return = (
        points[-1].equal_weight_index / points[0].equal_weight_index
        - Decimal("1")
    ).quantize(VALUE_PRECISION)
    return PortfolioPerformanceMetrics(
        points=points,
        risk=risk,
        equal_weight_return=equal_weight_return,
    )


def _empty_metrics() -> PortfolioPerformanceMetrics:
    return PortfolioPerformanceMetrics(
        points=[],
        risk=calculate_nav_risk([]),
        equal_weight_return=None,
    )
