from decimal import Decimal

from app.core.config.settings import Settings
from app.core.notification.schemas import (
    NotificationChannel,
    NotificationTestResult,
)
from app.core.notification.service import NotificationService
from app.plugins.fund.interfaces.schemas import (
    FundDailyReportRead,
    FundDailySnapshotRead,
)


class FundDailyNotificationService:
    def __init__(self, settings: Settings) -> None:
        self._notification_service = NotificationService(settings=settings)

    def send(
        self,
        *,
        report: FundDailyReportRead,
        channel: NotificationChannel,
        snapshot: FundDailySnapshotRead | None = None,
    ) -> NotificationTestResult:
        return self._notification_service.send_test(
            channel=channel,
            title=f"HAP 基金日报 · {report.report_date}",
            message=self._build_message(report, snapshot=snapshot),
            source="fund_daily_report",
        )

    @classmethod
    def _build_message(
        cls,
        report: FundDailyReportRead,
        *,
        snapshot: FundDailySnapshotRead | None = None,
    ) -> str:
        holding = report.holding_summary
        allocation = report.allocation
        holding_risk = report.holding_risk
        nav = report.nav_summary
        lines = [
            f"报告日期：{report.report_date}",
            f"持仓：{holding.position_count} 条 / {holding.fund_count} 只基金",
            f"持仓成本：{cls._format_money(holding.total_cost)}",
            f"当前估值：{cls._format_money(holding.current_value)}",
            f"浮盈亏：{cls._format_money(holding.unrealized_profit, signed=True)}",
            f"收益率：{cls._format_percent(holding.unrealized_return_rate, signed=True)}",
            f"估值完整度：{allocation.current_nav_count}/{allocation.position_count}",
            f"最大单基金：{cls._format_percent(allocation.top_holding_weight)}",
            (
                "风险覆盖："
                f"{holding_risk.analyzed_fund_count}/{holding_risk.fund_count} 只基金"
            ),
            f"最新净值：{nav.latest_nav_date or '--'}",
            f"观察池：{report.watchlist_summary.item_count} 只",
            f"交易流水：{report.transaction_summary.transaction_count} 条",
            (
                "净现金流："
                f"{cls._format_money(report.transaction_summary.net_cash_flow, signed=True)}"
            ),
        ]
        risk_items = [
            item
            for item in holding_risk.items
            if item.calculation_available
        ]
        if risk_items:
            highest_volatility = max(
                risk_items,
                key=lambda item: item.annualized_volatility or Decimal("-1"),
            )
            deepest_drawdown = min(
                risk_items,
                key=lambda item: item.maximum_drawdown or Decimal("0"),
            )
            lines.extend(
                [
                    (
                        "最高年化波动："
                        f"{highest_volatility.fund_name} "
                        f"{cls._format_percent(highest_volatility.annualized_volatility)}"
                    ),
                    (
                        "样本内最大回撤："
                        f"{deepest_drawdown.fund_name} "
                        f"{cls._format_percent(deepest_drawdown.maximum_drawdown)}"
                    ),
                ]
            )
        if snapshot is not None and snapshot.change_from_previous is not None:
            change = snapshot.change_from_previous
            lines.extend(
                [
                    "",
                    "较前次快照：",
                    f"• 当前估值 {cls._format_money(change.current_value, signed=True)}",
                    f"• 浮盈亏 {cls._format_money(change.unrealized_profit, signed=True)}",
                    (
                        "• 收益率 "
                        f"{cls._format_percentage_point_change(change.unrealized_return_rate)}"
                    ),
                    f"• 持仓数量 {change.position_count:+d} 条",
                ]
            )
        if report.alerts:
            lines.extend(["", "数据提醒："])
            lines.extend(f"• {alert.message}" for alert in report.alerts)
        lines.extend(
            [
                "",
                "数据来自 HAP 已保存记录，不代表实时行情或投资建议。",
            ]
        )
        return "\n".join(lines)

    @staticmethod
    def _format_money(value: Decimal | None, *, signed: bool = False) -> str:
        if value is None:
            return "--"
        prefix = "+" if signed and value > 0 else "-" if signed and value < 0 else ""
        display_value = abs(value) if signed else value
        return f"{prefix}¥{display_value:,.2f}"

    @staticmethod
    def _format_percent(value: Decimal | None, *, signed: bool = False) -> str:
        if value is None:
            return "--"
        prefix = "+" if signed and value > 0 else ""
        return f"{prefix}{value * 100:.2f}%"

    @staticmethod
    def _format_percentage_point_change(value: Decimal | None) -> str:
        if value is None:
            return "--"
        prefix = "+" if value > 0 else ""
        return f"{prefix}{value * 100:.2f} 个百分点"
