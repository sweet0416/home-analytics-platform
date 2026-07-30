from datetime import date
from decimal import Decimal

from app.plugins.fund.infrastructure.sources.eastmoney_holdings import (
    EastmoneyFundHoldingsSource,
)


def test_holdings_source_parses_latest_quarter_by_header_name() -> None:
    content = """
    <html><body>
      <div class="boxitem">
        <h4 class="t">
          <label><a title="Sample Fund">Sample Fund</a> 2026年1季度股票投资明细</label>
          <label>来源：天天基金 截止至：2026-03-31</label>
        </h4>
        <table class="tzxq">
          <thead><tr>
            <th>序号</th><th>股票代码</th><th>股票名称</th>
            <th>相关资讯</th><th>占净值 比例</th>
            <th>持股数 （万股）</th><th>持仓市值 （万元）</th>
          </tr></thead>
          <tbody><tr>
            <td>1</td><td>OLD</td><td>Old Asset</td><td>-</td>
            <td>1.00%</td><td>2</td><td>3</td>
          </tr></tbody>
        </table>
      </div>
      <div class="boxitem">
        <h4 class="t">
          <label><a title="Sample Fund">Sample Fund</a> 2026年2季度股票投资明细</label>
          <label>来源：天天基金 截止至：2026-06-30</label>
        </h4>
        <table class="tzxq">
          <thead><tr>
            <th>序号</th><th>股票代码</th><th>股票名称</th>
            <th>最新价</th><th>涨跌幅</th><th>相关资讯</th>
            <th>占净值 比例</th><th>持股数 （万股）</th>
            <th>持仓市值 （万元）</th>
          </tr></thead>
          <tbody><tr>
            <td>1</td><td>300308</td><td>中际旭创</td><td>100</td>
            <td>1%</td><td>-</td><td>9.72%</td><td>40.49</td>
            <td>51,422.94</td>
          </tr></tbody>
        </table>
      </div>
    </body></html>
    """

    disclosure = EastmoneyFundHoldingsSource.parse_page(
        content,
        source_url="https://example.test/holdings",
        fund_code="009777",
    )

    assert disclosure.fund_name == "Sample Fund"
    assert disclosure.report_date == date(2026, 6, 30)
    assert disclosure.report_period == "2026Q2"
    assert disclosure.holdings[0].asset_code == "300308"
    assert disclosure.holdings[0].nav_ratio == Decimal("0.09720000")
    assert disclosure.holdings[0].reported_quantity == Decimal("40.4900")
    assert disclosure.holdings[0].reported_market_value == Decimal("51422.9400")


def test_holdings_source_decodes_eastmoney_script_wrapper() -> None:
    content = (
        'var apidata={ content:"<div class=\\"sample\\">value</div>",'
        'arryear:[2026],curyear:2026};'
    )

    extracted = EastmoneyFundHoldingsSource._extract_response_html(content)

    assert extracted == '<div class="sample">value</div>'
