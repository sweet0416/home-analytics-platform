from loguru import logger

from app.core.config.settings import Settings
from app.core.notification.schemas import NotificationChannel
from app.core.notification.service import NotificationService
from app.plugins.lottery.application.services import LotteryService


class DltNotificationService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def notify_sync_result(
        self,
        *,
        service: LotteryService,
        result: dict[str, object],
        trigger_type: str,
    ) -> None:
        if not self._settings.lottery_dlt_notify_enabled:
            return

        status = str(result.get("status") or "unknown")
        if status == "failed":
            self._send(
                title=f"大乐透{trigger_type}同步失败",
                message=str(result.get("error_message") or "同步失败，请查看 HAP 同步日志。"),
            )
            return

        inserted_issues = self._extract_inserted_issue_numbers(result)
        if not inserted_issues:
            if self._settings.lottery_dlt_notify_on_no_changes:
                self._send(
                    title=f"大乐透{trigger_type}同步完成",
                    message="本次同步没有发现新的开奖数据。",
                )
            return

        latest_issue_no = max(inserted_issues)
        draw = service.get_draw_by_issue(latest_issue_no)
        message = "\n".join(
            [
                f"期号：{draw['issue_no']}",
                f"开奖日期：{draw['draw_date']}",
                f"前区：{self._format_numbers(draw['front_numbers'])}",
                f"后区：{self._format_numbers(draw['back_numbers'])}",
                f"本次新增：{len(inserted_issues)} 期",
            ]
        )
        self._send(
            title=f"大乐透 {draw['issue_no']} 开奖",
            message=message,
        )

    def notify_sync_exception(self, *, trigger_type: str, exc: Exception) -> None:
        if not self._settings.lottery_dlt_notify_enabled:
            return

        self._send(
            title=f"大乐透{trigger_type}同步异常",
            message=f"同步任务发生异常：{exc}",
        )

    @staticmethod
    def _extract_inserted_issue_numbers(result: dict[str, object]) -> list[str]:
        details = result.get("details")
        if not isinstance(details, list):
            return []

        issues: list[str] = []
        for item in details:
            if not isinstance(item, dict):
                continue
            if item.get("action") != "inserted":
                continue
            issue_no = item.get("issue_no")
            if issue_no is not None:
                issues.append(str(issue_no))
        return issues

    def _send(self, *, title: str, message: str) -> None:
        try:
            channel = NotificationChannel(self._settings.lottery_dlt_notify_channel)
        except ValueError:
            logger.warning(
                "Invalid DLT notification channel={}, fallback to all.",
                self._settings.lottery_dlt_notify_channel,
            )
            channel = NotificationChannel.all

        result = NotificationService(settings=self._settings).send_test(
            channel=channel,
            title=title,
            message=message,
        )
        logger.info("DLT notification finished: {}", result.model_dump())

    @staticmethod
    def _format_numbers(value: object) -> str:
        if not isinstance(value, list):
            return "-"
        numbers = [int(number) for number in value if isinstance(number, int)]
        return " ".join(f"{number:02d}" for number in numbers)
