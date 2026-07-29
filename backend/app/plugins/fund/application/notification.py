from decimal import Decimal

from app.core.config.settings import Settings
from app.core.notification.schemas import (
    NotificationChannel,
    NotificationTestResult,
)
from app.core.notification.service import NotificationService
from app.plugins.fund.interfaces.schemas import FundDailyReportRead


class FundDailyNotificationService:
    def __init__(self, settings: Settings) -> None:
        self._notification_service = NotificationService(settings=settings)

    def send(
        self,
        *,
        report: FundDailyReportRead,
        channel: NotificationChannel,
    ) -> NotificationTestResult:
        return self._notification_service.send_test(
            channel=channel,
            title=f"HAP 基金日报 · {report.report_date}",
            message=self._build_message(report),
            source="fund_daily_report",
        )

    @classmethod
    def _build_message(cls, report: FundDailyReportRead) -> str:
        holding = report.holding_summary
        allocation = report.allocation
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
            f"最新净值：{nav.latest_nav_date or '--'}",
            f"观察池：{report.watchlist_summary.item_count} 只",
            f"交易流水：{report.transaction_summary.transaction_count} 条",
            (
                "净现金流："
                f"{cls._format_money(report.transaction_summary.net_cash_flow, signed=True)}"
            ),
        ]
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
