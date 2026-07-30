from dataclasses import dataclass
from datetime import date
from decimal import Decimal

VALUE_PRECISION = Decimal("0.00000001")


@dataclass(frozen=True)
class LookthroughHolding:
    asset_code: str
    asset_name: str
    nav_ratio: Decimal


@dataclass(frozen=True)
class LookthroughFundDisclosure:
    fund_code: str
    allocation_weight: Decimal
    report_date: date
    holdings: list[LookthroughHolding]


@dataclass(frozen=True)
class LookthroughAsset:
    asset_code: str
    asset_name: str
    portfolio_weight: Decimal
    fund_count: int


@dataclass(frozen=True)
class LookthroughMetrics:
    coverage_weight: Decimal
    disclosed_weight: Decimal
    assets: list[LookthroughAsset]
    included_fund_codes: list[str]
    stale_fund_codes: list[str]


def calculate_lookthrough(
    disclosures: list[LookthroughFundDisclosure],
    *,
    as_of_date: date,
    stale_after_days: int = 180,
) -> LookthroughMetrics:
    exposure_by_asset: dict[str, tuple[str, Decimal, set[str]]] = {}
    included: list[str] = []
    stale: list[str] = []
    coverage_weight = Decimal("0")

    for disclosure in disclosures:
        age_days = (as_of_date - disclosure.report_date).days
        if age_days < 0 or age_days > stale_after_days:
            stale.append(disclosure.fund_code)
            continue
        included.append(disclosure.fund_code)
        coverage_weight += disclosure.allocation_weight
        for holding in disclosure.holdings:
            name, weight, fund_codes = exposure_by_asset.get(
                holding.asset_code,
                (holding.asset_name, Decimal("0"), set()),
            )
            fund_codes.add(disclosure.fund_code)
            exposure_by_asset[holding.asset_code] = (
                name,
                weight + disclosure.allocation_weight * holding.nav_ratio,
                fund_codes,
            )

    assets = [
        LookthroughAsset(
            asset_code=asset_code,
            asset_name=name,
            portfolio_weight=weight.quantize(VALUE_PRECISION),
            fund_count=len(fund_codes),
        )
        for asset_code, (name, weight, fund_codes) in exposure_by_asset.items()
    ]
    assets.sort(key=lambda item: (-item.portfolio_weight, item.asset_code))
    return LookthroughMetrics(
        coverage_weight=coverage_weight.quantize(VALUE_PRECISION),
        disclosed_weight=sum(
            (item.portfolio_weight for item in assets),
            Decimal("0"),
        ).quantize(VALUE_PRECISION),
        assets=assets,
        included_fund_codes=sorted(included),
        stale_fund_codes=sorted(stale),
    )
