import json
from decimal import Decimal

import pytest

from app.plugins.fund.domain.target_links import parse_target_fund_links


def test_parse_target_fund_links() -> None:
    links = parse_target_fund_links(
        json.dumps(
            [
                {
                    "parent_fund_code": "050025",
                    "target_fund_code": "513500",
                    "target_fund_name": "Target ETF",
                    "target_allocation_ratio": "0.9402",
                    "report_date": "2026-03-31",
                    "source_url": "https://example.test/report.pdf",
                }
            ]
        )
    )

    assert links[0].parent_fund_code == "050025"
    assert links[0].target_fund_code == "513500"
    assert links[0].target_allocation_ratio == Decimal("0.9402")
    assert links[0].report_date.isoformat() == "2026-03-31"


@pytest.mark.parametrize(
    "payload",
    [
        "not-json",
        "{}",
        '[{"parent_fund_code":"A"}]',
        (
            '[{"parent_fund_code":"A","target_fund_code":"B",'
            '"target_fund_name":"ETF","target_allocation_ratio":"1.1",'
            '"report_date":"2026-01-01","source_url":"https://example.test"}]'
        ),
    ],
)
def test_parse_target_fund_links_rejects_invalid_config(payload: str) -> None:
    with pytest.raises(ValueError):
        parse_target_fund_links(payload)
