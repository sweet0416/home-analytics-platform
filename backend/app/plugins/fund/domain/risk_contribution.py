from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from itertools import pairwise

TRADING_DAYS_PER_YEAR = Decimal("252")
VALUE_PRECISION = Decimal("0.000001")


@dataclass(frozen=True)
class FundRiskContributionSeries:
    fund_code: str
    weight: Decimal
    observations: list[tuple[date, Decimal]]


@dataclass(frozen=True)
class FundRiskContributionItem:
    fund_code: str
    allocation_weight: Decimal
    annualized_volatility: Decimal
    component_volatility: Decimal
    contribution_ratio: Decimal


@dataclass(frozen=True)
class FundRiskContributionMetrics:
    sample_count: int
    start_date: date | None
    end_date: date | None
    portfolio_annualized_volatility: Decimal | None
    weighted_standalone_volatility: Decimal | None
    diversification_ratio: Decimal | None
    items: list[FundRiskContributionItem]


def calculate_risk_contributions(
    series: list[FundRiskContributionSeries],
) -> FundRiskContributionMetrics:
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
    if len(ordered_dates) < 3:
        return _empty_metrics()

    total_weight = sum((item.weight for item, _ in prepared), Decimal("0"))
    normalized_weights = [
        item.weight / total_weight for item, _ in prepared
    ]
    returns = [
        [
            observations[current_date] / observations[previous_date]
            - Decimal("1")
            for previous_date, current_date in pairwise(ordered_dates)
        ]
        for _, observations in prepared
    ]
    covariance_matrix = _annualized_covariance_matrix(returns)
    portfolio_variance = sum(
        (
            normalized_weights[row_index]
            * normalized_weights[column_index]
            * covariance_matrix[row_index][column_index]
            for row_index in range(len(prepared))
            for column_index in range(len(prepared))
        ),
        Decimal("0"),
    )
    if portfolio_variance <= 0:
        return FundRiskContributionMetrics(
            sample_count=len(returns[0]),
            start_date=ordered_dates[1],
            end_date=ordered_dates[-1],
            portfolio_annualized_volatility=None,
            weighted_standalone_volatility=None,
            diversification_ratio=None,
            items=[],
        )

    portfolio_volatility = portfolio_variance.sqrt()
    standalone_volatilities = [
        max(covariance_matrix[index][index], Decimal("0")).sqrt()
        for index in range(len(prepared))
    ]
    weighted_standalone = sum(
        (
            weight * volatility
            for weight, volatility in zip(
                normalized_weights,
                standalone_volatilities,
                strict=True,
            )
        ),
        Decimal("0"),
    )
    items: list[FundRiskContributionItem] = []
    for index, ((item, _), weight) in enumerate(
        zip(prepared, normalized_weights, strict=True)
    ):
        covariance_with_portfolio = sum(
            (
                covariance_matrix[index][other_index]
                * normalized_weights[other_index]
                for other_index in range(len(prepared))
            ),
            Decimal("0"),
        )
        variance_contribution = weight * covariance_with_portfolio
        items.append(
            FundRiskContributionItem(
                fund_code=item.fund_code,
                allocation_weight=weight.quantize(VALUE_PRECISION),
                annualized_volatility=standalone_volatilities[index].quantize(
                    VALUE_PRECISION
                ),
                component_volatility=(
                    variance_contribution / portfolio_volatility
                ).quantize(VALUE_PRECISION),
                contribution_ratio=(
                    variance_contribution / portfolio_variance
                ).quantize(VALUE_PRECISION),
            )
        )

    return FundRiskContributionMetrics(
        sample_count=len(returns[0]),
        start_date=ordered_dates[1],
        end_date=ordered_dates[-1],
        portfolio_annualized_volatility=portfolio_volatility.quantize(
            VALUE_PRECISION
        ),
        weighted_standalone_volatility=weighted_standalone.quantize(
            VALUE_PRECISION
        ),
        diversification_ratio=(
            weighted_standalone / portfolio_volatility
        ).quantize(VALUE_PRECISION),
        items=items,
    )


def _annualized_covariance_matrix(
    returns: list[list[Decimal]],
) -> list[list[Decimal]]:
    observation_count = len(returns[0])
    means = [
        sum(values, Decimal("0")) / Decimal(observation_count)
        for values in returns
    ]
    return [
        [
            (
                sum(
                    (
                        (first - means[row_index])
                        * (second - means[column_index])
                        for first, second in zip(
                            returns[row_index],
                            returns[column_index],
                            strict=True,
                        )
                    ),
                    Decimal("0"),
                )
                / Decimal(observation_count - 1)
                * TRADING_DAYS_PER_YEAR
            )
            for column_index in range(len(returns))
        ]
        for row_index in range(len(returns))
    ]


def _empty_metrics() -> FundRiskContributionMetrics:
    return FundRiskContributionMetrics(
        sample_count=0,
        start_date=None,
        end_date=None,
        portfolio_annualized_volatility=None,
        weighted_standalone_volatility=None,
        diversification_ratio=None,
        items=[],
    )
