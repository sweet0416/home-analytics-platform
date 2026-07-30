from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from itertools import pairwise
from math import sqrt
from statistics import correlation, mean, stdev

TRADING_DAYS_PER_YEAR = 252
VALUE_PRECISION = Decimal("0.000001")
INDEX_BASE = Decimal("100")


@dataclass(frozen=True)
class PortfolioBenchmarkPoint:
    nav_date: date
    portfolio_index: Decimal
    benchmark_index: Decimal
    relative_return: Decimal


@dataclass(frozen=True)
class PortfolioBenchmarkMetrics:
    points: list[PortfolioBenchmarkPoint]
    portfolio_return: Decimal | None
    benchmark_return: Decimal | None
    relative_return: Decimal | None
    tracking_error: Decimal | None
    information_ratio: Decimal | None
    return_correlation: Decimal | None


def calculate_portfolio_benchmark(
    portfolio_observations: list[tuple[date, Decimal]],
    benchmark_observations: list[tuple[date, Decimal]],
) -> PortfolioBenchmarkMetrics:
    portfolio = {
        nav_date: value
        for nav_date, value in portfolio_observations
        if value > 0
    }
    benchmark = {
        nav_date: value
        for nav_date, value in benchmark_observations
        if value > 0
    }
    common_dates = sorted(set(portfolio).intersection(benchmark))
    if len(common_dates) < 2:
        return _empty_metrics()

    portfolio_base = portfolio[common_dates[0]]
    benchmark_base = benchmark[common_dates[0]]
    points: list[PortfolioBenchmarkPoint] = []
    for nav_date in common_dates:
        portfolio_index = INDEX_BASE * portfolio[nav_date] / portfolio_base
        benchmark_index = INDEX_BASE * benchmark[nav_date] / benchmark_base
        points.append(
            PortfolioBenchmarkPoint(
                nav_date=nav_date,
                portfolio_index=portfolio_index.quantize(VALUE_PRECISION),
                benchmark_index=benchmark_index.quantize(VALUE_PRECISION),
                relative_return=(
                    portfolio_index / benchmark_index - Decimal("1")
                ).quantize(VALUE_PRECISION),
            )
        )

    portfolio_returns = [
        float(current.portfolio_index / previous.portfolio_index - Decimal("1"))
        for previous, current in pairwise(points)
    ]
    benchmark_returns = [
        float(current.benchmark_index / previous.benchmark_index - Decimal("1"))
        for previous, current in pairwise(points)
    ]
    active_returns = [
        portfolio_return - benchmark_return
        for portfolio_return, benchmark_return in zip(
            portfolio_returns,
            benchmark_returns,
            strict=True,
        )
    ]
    tracking_error_value = (
        stdev(active_returns) * sqrt(TRADING_DAYS_PER_YEAR)
        if len(active_returns) >= 2
        else None
    )
    information_ratio_value = (
        mean(active_returns) * TRADING_DAYS_PER_YEAR / tracking_error_value
        if tracking_error_value not in (None, 0)
        else None
    )
    correlation_value = (
        correlation(portfolio_returns, benchmark_returns)
        if len(portfolio_returns) >= 2
        and stdev(portfolio_returns) > 0
        and stdev(benchmark_returns) > 0
        else None
    )

    return PortfolioBenchmarkMetrics(
        points=points,
        portfolio_return=(
            points[-1].portfolio_index / points[0].portfolio_index
            - Decimal("1")
        ).quantize(VALUE_PRECISION),
        benchmark_return=(
            points[-1].benchmark_index / points[0].benchmark_index
            - Decimal("1")
        ).quantize(VALUE_PRECISION),
        relative_return=points[-1].relative_return,
        tracking_error=_to_decimal(tracking_error_value),
        information_ratio=_to_decimal(information_ratio_value),
        return_correlation=_to_decimal(correlation_value),
    )


def _to_decimal(value: float | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value)).quantize(VALUE_PRECISION)


def _empty_metrics() -> PortfolioBenchmarkMetrics:
    return PortfolioBenchmarkMetrics(
        points=[],
        portfolio_return=None,
        benchmark_return=None,
        relative_return=None,
        tracking_error=None,
        information_ratio=None,
        return_correlation=None,
    )
