from loguru import logger

from app.core.config.settings import Settings
from app.core.notification.schemas import NotificationChannel
from app.core.notification.service import NotificationService
from app.plugins.lottery.application.services import LotteryService

MANUAL_TRIGGER = "\u624b\u52a8"
SCHEDULED_TRIGGER = "\u5b9a\u65f6"


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
                title=f"\u5927\u4e50\u900f{trigger_type}\u540c\u6b65\u5931\u8d25",
                message=str(
                    result.get("error_message")
                    or "\u540c\u6b65\u5931\u8d25\uff0c\u8bf7\u67e5\u770b HAP \u540c\u6b65\u65e5\u5fd7\u3002"
                ),
            )
            return

        inserted_issues = self._extract_issue_numbers(result, "inserted")
        updated_issues = self._extract_issue_numbers(result, "updated")
        skipped_count = self._as_int(result.get("skipped_count"))
        should_notify_no_changes = (
            trigger_type == MANUAL_TRIGGER or self._settings.lottery_dlt_notify_on_no_changes
        )
        if not inserted_issues and not updated_issues:
            if should_notify_no_changes:
                self._send(
                    title=f"\u5927\u4e50\u900f{trigger_type}\u540c\u6b65\u5b8c\u6210",
                    message="\n".join(
                        [
                            "\u672c\u6b21\u6ca1\u6709\u53d1\u73b0\u65b0\u7684\u5f00\u5956\u6570\u636e\u3002",
                            "\u65b0\u589e\uff1a0 \u671f",
                            "\u66f4\u65b0\uff1a0 \u671f",
                            f"\u8df3\u8fc7\uff1a{skipped_count} \u671f",
                        ]
                    ),
                )
            return

        latest_issue_no = max(inserted_issues or updated_issues)
        draw = service.get_draw_by_issue(latest_issue_no)
        message = "\n".join(
            [
                f"\u671f\u53f7\uff1a{draw['issue_no']}",
                f"\u5f00\u5956\u65e5\u671f\uff1a{draw['draw_date']}",
                f"\u524d\u533a\uff1a{self._format_numbers(draw['front_numbers'])}",
                f"\u540e\u533a\uff1a{self._format_numbers(draw['back_numbers'])}",
                f"\u65b0\u589e\uff1a{len(inserted_issues)} \u671f",
                f"\u66f4\u65b0\uff1a{len(updated_issues)} \u671f",
                f"\u8df3\u8fc7\uff1a{skipped_count} \u671f",
            ]
        )
        self._send(
            title=f"\u5927\u4e50\u900f {draw['issue_no']} \u5f00\u5956",
            message=message,
        )

    def notify_sync_exception(self, *, trigger_type: str, exc: Exception) -> None:
        if not self._settings.lottery_dlt_notify_enabled:
            return

        self._send(
            title=f"\u5927\u4e50\u900f{trigger_type}\u540c\u6b65\u5f02\u5e38",
            message=f"\u540c\u6b65\u4efb\u52a1\u53d1\u751f\u5f02\u5e38\uff1a{exc}",
        )

    @staticmethod
    def _extract_issue_numbers(result: dict[str, object], action: str) -> list[str]:
        details = result.get("details")
        if not isinstance(details, list):
            return []

        issues: list[str] = []
        for item in details:
            if not isinstance(item, dict):
                continue
            if item.get("action") != action:
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
            source="lottery_dlt_sync",
        )
        logger.info("DLT notification finished: {}", result.model_dump())

    @staticmethod
    def _format_numbers(value: object) -> str:
        if not isinstance(value, list):
            return "-"
        numbers = [int(number) for number in value if isinstance(number, int)]
        return " ".join(f"{number:02d}" for number in numbers)

    @staticmethod
    def _as_int(value: object) -> int:
        if isinstance(value, int):
            return value
        return 0
