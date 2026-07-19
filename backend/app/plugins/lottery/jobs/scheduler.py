from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from app.core.config.settings import Settings, get_settings
from app.core.database.session import SessionLocal
from app.core.notification.schemas import NotificationChannel
from app.core.notification.service import NotificationService
from app.plugins.lottery.application.services import LotteryService
from app.plugins.lottery.domain.sync import DrawSyncCommand

_scheduler: BackgroundScheduler | None = None


def start_lottery_scheduler() -> None:
    settings = get_settings()
    if not settings.lottery_dlt_auto_sync_enabled:
        logger.info("DLT auto sync is disabled.")
        return

    global _scheduler
    if _scheduler is not None and _scheduler.running:
        logger.info("DLT auto sync scheduler is already running.")
        return

    scheduler = BackgroundScheduler(timezone="Asia/Shanghai")
    scheduler.add_job(
        _run_scheduled_dlt_sync,
        CronTrigger.from_crontab(settings.lottery_dlt_sync_cron, timezone="Asia/Shanghai"),
        id="lottery_dlt_auto_sync",
        name="DLT draw auto sync",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    _scheduler = scheduler
    logger.info("DLT auto sync scheduler started: {}", settings.lottery_dlt_sync_cron)


def stop_lottery_scheduler() -> None:
    global _scheduler
    if _scheduler is None:
        return

    if _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("DLT auto sync scheduler stopped.")
    _scheduler = None


def get_lottery_scheduler_status() -> dict[str, object]:
    settings = get_settings()
    job = _scheduler.get_job("lottery_dlt_auto_sync") if _scheduler is not None else None
    return {
        "enabled": settings.lottery_dlt_auto_sync_enabled,
        "running": bool(_scheduler is not None and _scheduler.running),
        "cron": settings.lottery_dlt_sync_cron,
        "timezone": "Asia/Shanghai",
        "page_size": settings.lottery_dlt_sync_page_size,
        "next_run_at": job.next_run_time.isoformat() if job and job.next_run_time else None,
    }


def _run_scheduled_dlt_sync() -> None:
    settings = get_settings()
    db = SessionLocal()
    try:
        logger.info("Starting scheduled DLT draw sync.")
        service = LotteryService(db)
        result = service.sync_draws(
            DrawSyncCommand(
                sync_type="scheduled",
                page=1,
                page_size=settings.lottery_dlt_sync_page_size,
                force=False,
            )
        )
        logger.info("Scheduled DLT draw sync finished: {}", result)
        _notify_scheduled_sync_result(service=service, settings=settings, result=result)
    except Exception as exc:
        logger.exception("Scheduled DLT draw sync failed: {}", exc)
        _notify_scheduled_sync_exception(settings=settings, exc=exc)
    finally:
        db.close()


def _notify_scheduled_sync_result(
    *,
    service: LotteryService,
    settings: Settings,
    result: dict[str, object],
) -> None:
    if not settings.lottery_dlt_notify_enabled:
        return

    status = str(result.get("status") or "unknown")
    if status == "failed":
        _send_lottery_notification(
            settings=settings,
            title="大乐透同步失败",
            message=str(result.get("error_message") or "定时同步失败，请查看 HAP 同步日志。"),
        )
        return

    inserted_issues = _extract_inserted_issue_numbers(result)
    if not inserted_issues:
        if settings.lottery_dlt_notify_on_no_changes:
            _send_lottery_notification(
                settings=settings,
                title="大乐透同步完成",
                message="本次同步没有发现新的开奖数据。",
            )
        return

    latest_issue_no = max(inserted_issues)
    draw = service.get_draw_by_issue(latest_issue_no)
    front_numbers = _format_numbers(draw["front_numbers"])
    back_numbers = _format_numbers(draw["back_numbers"])
    message = "\n".join(
        [
            f"期号：{draw['issue_no']}",
            f"开奖日期：{draw['draw_date']}",
            f"前区：{front_numbers}",
            f"后区：{back_numbers}",
            f"本次新增：{len(inserted_issues)} 期",
        ]
    )
    _send_lottery_notification(
        settings=settings,
        title=f"大乐透 {draw['issue_no']} 开奖",
        message=message,
    )


def _notify_scheduled_sync_exception(*, settings: Settings, exc: Exception) -> None:
    if not settings.lottery_dlt_notify_enabled:
        return

    _send_lottery_notification(
        settings=settings,
        title="大乐透同步异常",
        message=f"定时同步任务发生异常：{exc}",
    )


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


def _send_lottery_notification(*, settings: Settings, title: str, message: str) -> None:
    try:
        channel = NotificationChannel(settings.lottery_dlt_notify_channel)
    except ValueError:
        logger.warning(
            "Invalid DLT notification channel={}, fallback to all.",
            settings.lottery_dlt_notify_channel,
        )
        channel = NotificationChannel.all

    result = NotificationService(settings=settings).send_test(
        channel=channel,
        title=title,
        message=message,
    )
    logger.info("DLT notification finished: {}", result.model_dump())


def _format_numbers(value: object) -> str:
    if not isinstance(value, list):
        return "-"
    numbers = [int(number) for number in value if isinstance(number, int)]
    return " ".join(f"{number:02d}" for number in numbers)
