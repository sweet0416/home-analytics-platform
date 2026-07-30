from datetime import date
from decimal import Decimal

from app.plugins.fund.domain.risk_contribution import (
    FundRiskContributionSeries,
    calculate_risk_contributions,
)


def test_risk_contribution_sums_to_portfolio_volatility() -> None:
    observations = [
        (date(2026, 7, 1), Decimal("100")),
        (date(2026, 7, 2), Decimal("110")),
        (date(2026, 7, 3), Decimal("99")),
        (date(2026, 7, 4), Decimal("118.8")),
    ]
    metrics = calculate_risk_contributions(
        [
            FundRiskContributionSeries(
                fund_code="A",
                weight=Decimal("0.75"),
                observations=observations,
            ),
            FundRiskContributionSeries(
                fund_code="B",
                weight=Decimal("0.25"),
                observations=observations,
            ),
        ]
    )

    assert metrics.sample_count == 3
    assert metrics.portfolio_annualized_volatility is not None
    assert metrics.diversification_ratio == Decimal("1.000000")
    assert sum(
        (item.component_volatility for item in metrics.items),
        Decimal("0"),
    ) == metrics.portfolio_annualized_volatility
    assert [item.contribution_ratio for item in metrics.items] == [
        Decimal("0.750000"),
        Decimal("0.250000"),
    ]


def test_risk_contribution_attributes_constant_fund_no_risk() -> None:
    metrics = calculate_risk_contributions(
        [
            FundRiskContributionSeries(
                fund_code="A",
                weight=Decimal("0.5"),
                observations=[
                    (date(2026, 7, 1), Decimal("100")),
                    (date(2026, 7, 2), Decimal("110")),
                    (date(2026, 7, 3), Decimal("99")),
                    (date(2026, 7, 4), Decimal("118.8")),
                ],
            ),
            FundRiskContributionSeries(
                fund_code="B",
                weight=Decimal("0.5"),
                observations=[
                    (date(2026, 7, 1), Decimal("100")),
                    (date(2026, 7, 2), Decimal("100")),
                    (date(2026, 7, 3), Decimal("100")),
                    (date(2026, 7, 4), Decimal("100")),
                ],
            ),
        ]
    )

    assert metrics.items[0].contribution_ratio == Decimal("1.000000")
    assert metrics.items[1].annualized_volatility == Decimal("0.000000")
    assert metrics.items[1].contribution_ratio == Decimal("0.000000")


def test_risk_contribution_requires_three_common_nav_dates() -> None:
    metrics = calculate_risk_contributions(
        [
            FundRiskContributionSeries(
                fund_code="A",
                weight=Decimal("1"),
                observations=[
                    (date(2026, 7, 1), Decimal("1")),
                    (date(2026, 7, 2), Decimal("1.1")),
                ],
            )
        ]
    )

    assert metrics.sample_count == 0
    assert metrics.portfolio_annualized_volatility is None
    assert metrics.items == []
