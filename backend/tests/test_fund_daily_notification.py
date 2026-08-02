from decimal import Decimal
from types import SimpleNamespace

from app.plugins.fund.application.notification import FundDailyNotificationService


def test_daily_notification_includes_snapshot_change_summary() -> None:
    report = SimpleNamespace(
        report_date="2026-08-02",
        holding_summary=SimpleNamespace(
            position_count=4,
            fund_count=4,
            total_cost=Decimal("4237.40"),
            current_value=Decimal("3657.64"),
            unrealized_profit=Decimal("-579.76"),
            unrealized_return_rate=Decimal("-0.1368"),
        ),
        allocation=SimpleNamespace(
            current_nav_count=4,
            position_count=4,
            top_holding_weight=Decimal("0.35"),
        ),
        holding_risk=SimpleNamespace(
            analyzed_fund_count=4,
            fund_count=4,
            items=[],
        ),
        nav_summary=SimpleNamespace(latest_nav_date="2026-07-31"),
        watchlist_summary=SimpleNamespace(item_count=0),
        transaction_summary=SimpleNamespace(
            transaction_count=4,
            net_cash_flow=Decimal("4237.40"),
        ),
        alerts=[],
    )
    snapshot = SimpleNamespace(
        change_from_previous=SimpleNamespace(
            current_value=Decimal("23.50"),
            unrealized_profit=Decimal("23.50"),
            unrealized_return_rate=Decimal("0.0056"),
            position_count=0,
        )
    )
    insights = SimpleNamespace(
        comparisons=[
            SimpleNamespace(
                period_days=7,
                change=SimpleNamespace(
                    current_value=Decimal("35.00"),
                    unrealized_return_rate=Decimal("0.0075"),
                ),
            ),
            SimpleNamespace(period_days=30, change=None),
        ],
        alerts=[SimpleNamespace(message="数据完整度较前次快照下降。")],
    )

    message = FundDailyNotificationService._build_message(
        report,
        snapshot=snapshot,
        insights=insights,
    )

    assert "较前次快照：" in message
    assert "当前估值 +¥23.50" in message
    assert "浮盈亏 +¥23.50" in message
    assert "收益率 +0.56 个百分点" in message
    assert "持仓数量 +0 条" in message
    assert "阶段变化：" in message
    assert "近 7 日：估值 +¥35.00，收益率 +0.75 个百分点" in message
    assert "变化提醒：" in message
    assert "数据完整度较前次快照下降。" in message


def test_daily_notification_omits_change_section_without_previous_snapshot() -> None:
    report = SimpleNamespace(
        report_date="2026-08-02",
        holding_summary=SimpleNamespace(
            position_count=0,
            fund_count=0,
            total_cost=Decimal("0"),
            current_value=None,
            unrealized_profit=None,
            unrealized_return_rate=None,
        ),
        allocation=SimpleNamespace(
            current_nav_count=0,
            position_count=0,
            top_holding_weight=None,
        ),
        holding_risk=SimpleNamespace(
            analyzed_fund_count=0,
            fund_count=0,
            items=[],
        ),
        nav_summary=SimpleNamespace(latest_nav_date=None),
        watchlist_summary=SimpleNamespace(item_count=0),
        transaction_summary=SimpleNamespace(
            transaction_count=0,
            net_cash_flow=Decimal("0"),
        ),
        alerts=[],
    )

    message = FundDailyNotificationService._build_message(report)

    assert "较前次快照：" not in message
