from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from itertools import pairwise
from math import sqrt
from statistics import stdev

RATE_PRECISION = Decimal("0.000001")
TRADING_DAYS_PER_YEAR = 252


@dataclass(frozen=True)
class FundNavRiskMetrics:
    sample_count: int
    return_observation_count: int
    start_date: date | None
    end_date: date | None
    cumulative_return: Decimal | None
    annualized_volatility: Decimal | None
    maximum_drawdown: Decimal | None
    drawdown_peak_date: date | None
    drawdown_trough_date: date | None
    positive_day_ratio: Decimal | None


def calculate_nav_risk(
    observations: list[tuple[date, Decimal]],
) -> FundNavRiskMetrics:
    ordered = sorted(observations, key=lambda item: item[0])
    if len(ordered) < 2:
        only_date = ordered[0][0] if ordered else None
        return FundNavRiskMetrics(
            sample_count=len(ordered),
            return_observation_count=0,
            start_date=only_date,
            end_date=only_date,
            cumulative_return=None,
            annualized_volatility=None,
            maximum_drawdown=None,
            drawdown_peak_date=None,
            drawdown_trough_date=None,
            positive_day_ratio=None,
        )

    daily_returns = [
        current_nav / previous_nav - Decimal("1")
        for (_, previous_nav), (_, current_nav) in pairwise(ordered)
    ]
    first_date, first_nav = ordered[0]
    end_date, last_nav = ordered[-1]
    peak_date = first_date
    peak_nav = first_nav
    maximum_drawdown = Decimal("0")
    drawdown_peak_date = first_date
    drawdown_trough_date = first_date

    for nav_date, nav in ordered[1:]:
        if nav > peak_nav:
            peak_nav = nav
            peak_date = nav_date
            continue
        drawdown = nav / peak_nav - Decimal("1")
        if drawdown < maximum_drawdown:
            maximum_drawdown = drawdown
            drawdown_peak_date = peak_date
            drawdown_trough_date = nav_date

    volatility = (
        Decimal(str(stdev(float(value) for value in daily_returns) * sqrt(TRADING_DAYS_PER_YEAR)))
        if len(daily_returns) >= 2
        else None
    )
    positive_day_ratio = Decimal(
        sum(value > 0 for value in daily_returns)
    ) / Decimal(len(daily_returns))

    return FundNavRiskMetrics(
        sample_count=len(ordered),
        return_observation_count=len(daily_returns),
        start_date=first_date,
        end_date=end_date,
        cumulative_return=(last_nav / first_nav - Decimal("1")).quantize(RATE_PRECISION),
        annualized_volatility=(
            volatility.quantize(RATE_PRECISION) if volatility is not None else None
        ),
        maximum_drawdown=maximum_drawdown.quantize(RATE_PRECISION),
        drawdown_peak_date=drawdown_peak_date if maximum_drawdown < 0 else None,
        drawdown_trough_date=drawdown_trough_date if maximum_drawdown < 0 else None,
        positive_day_ratio=positive_day_ratio.quantize(RATE_PRECISION),
    )
