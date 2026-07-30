from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from itertools import combinations, pairwise
from statistics import StatisticsError, correlation

CORRELATION_PRECISION = Decimal("0.000001")


@dataclass(frozen=True)
class FundCorrelationSeries:
    fund_code: str
    observations: list[tuple[date, Decimal]]


@dataclass(frozen=True)
class FundCorrelationPair:
    first_fund_code: str
    second_fund_code: str
    observation_count: int
    correlation: Decimal | None


def calculate_holding_correlations(
    series: list[FundCorrelationSeries],
) -> list[FundCorrelationPair]:
    prepared = {
        item.fund_code: {
            nav_date: nav
            for nav_date, nav in item.observations
            if nav > 0
        }
        for item in series
    }
    results: list[FundCorrelationPair] = []
    for first_code, second_code in combinations(sorted(prepared), 2):
        first = prepared[first_code]
        second = prepared[second_code]
        common_dates = sorted(set(first).intersection(second))
        first_returns = [
            first[current_date] / first[previous_date] - Decimal("1")
            for previous_date, current_date in pairwise(common_dates)
        ]
        second_returns = [
            second[current_date] / second[previous_date] - Decimal("1")
            for previous_date, current_date in pairwise(common_dates)
        ]
        value: Decimal | None = None
        if len(first_returns) >= 2:
            try:
                value = Decimal(
                    str(
                        correlation(
                            [float(item) for item in first_returns],
                            [float(item) for item in second_returns],
                        )
                    )
                ).quantize(CORRELATION_PRECISION)
            except StatisticsError:
                value = None
        results.append(
            FundCorrelationPair(
                first_fund_code=first_code,
                second_fund_code=second_code,
                observation_count=len(first_returns),
                correlation=value,
            )
        )
    return results
