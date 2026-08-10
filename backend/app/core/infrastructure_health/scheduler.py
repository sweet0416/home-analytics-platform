from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from app.core.config.settings import get_settings
from app.core.infrastructure_health.schemas import InfrastructureHealthRead
from app.core.infrastructure_health.service import InfrastructureHealthService
from app.core.notification.schemas import NotificationChannel
from app.core.notification.service import NotificationService

TIMEZONE = "Asia/Shanghai"
JOB_ID = "infrastructure_health_notify"

_scheduler: BackgroundScheduler | None = None
_last_run_at: datetime | None = None
_last_status: str | None = None
_last_message: str | None = None
_last_delivery_status: str | None = None


def start_infrastructure_health_scheduler() -> None:
    settings = get_settings()
    if not settings.infrastructure_health_notify_enabled:
        logger.info("Infrastructure health notification scheduler is disabled.")
        return

    global _scheduler
    if _scheduler is not None and _scheduler.running:
        logger.info("Infrastructure health notification scheduler is already running.")
        return

    scheduler = BackgroundScheduler(timezone=TIMEZONE)
    scheduler.add_job(
        _run_scheduled_health_check,
        CronTrigger.from_crontab(settings.infrastructure_health_notify_cron, timezone=TIMEZONE),
        id=JOB_ID,
        name="Infrastructure health notification",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    _scheduler = scheduler
    logger.info(
        "Infrastructure health notification scheduler started: {}",
        settings.infrastructure_health_notify_cron,
    )


def stop_infrastructure_health_scheduler() -> None:
    global _scheduler
    if _scheduler is None:
        return
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Infrastructure health notification scheduler stopped.")
    _scheduler = None


def get_infrastructure_health_scheduler_status() -> dict[str, object]:
    settings = get_settings()
    job = _scheduler.get_job(JOB_ID) if _scheduler is not None else None
    return {
        "enabled": settings.infrastructure_health_notify_enabled,
        "running": bool(_scheduler is not None and _scheduler.running),
        "cron": settings.infrastructure_health_notify_cron,
        "timezone": TIMEZONE,
        "channel": settings.infrastructure_health_notify_channel,
        "next_run_at": job.next_run_time if job and job.next_run_time else None,
        "last_run_at": _last_run_at,
        "last_status": _last_status,
        "last_message": _last_message,
        "last_delivery_status": _last_delivery_status,
    }


def _run_scheduled_health_check() -> None:
    global _last_delivery_status, _last_message, _last_run_at, _last_status
    _last_run_at = datetime.now()
    settings = get_settings()
    try:
        health = InfrastructureHealthService(settings).check()
        if health.configured_components == 0:
            _last_status = "skipped"
            _last_message = "No infrastructure plugin is configured."
            _last_delivery_status = None
            return

        channel = NotificationChannel(settings.infrastructure_health_notify_channel)
        message = build_health_notification_message(health)
        result = NotificationService(settings=settings).send_health_change(
            channel=channel,
            title=("HAP 基础设施恢复" if health.healthy else "HAP 基础设施异常"),
            message=message,
            healthy=health.healthy,
        )
        statuses = ", ".join(f"{item.channel.value} {item.status}" for item in result.results)
        _last_status = "healthy" if health.healthy else "unhealthy"
        _last_message = statuses or "no channel result"
        result_statuses = [item.status for item in result.results]
        if "failed" in result_statuses:
            _last_delivery_status = "failed"
        elif "sent" in result_statuses:
            _last_delivery_status = "sent"
        else:
            _last_delivery_status = "skipped"
        logger.info("Infrastructure health notification check finished: {}", _last_message)
    except Exception as exc:  # noqa: BLE001
        _last_status = "failed"
        _last_message = str(exc)
        logger.exception("Infrastructure health notification check failed: {}", exc)


def build_health_notification_message(health: InfrastructureHealthRead) -> str:
    healthy = health.healthy
    docker = health.docker
    pve = health.pve
    lines = [f"状态：{'正常' if healthy else '异常'}"]
    lines.append(
        "Docker："
        f"{'已连接' if docker.reachable else '连接异常'}，"
        f"容器 {docker.running}/{docker.containers}，异常 {docker.problematic} 个"
    )
    lines.append(f"PVE：{'已连接' if pve.reachable else '连接异常'}")
    if health.alerts:
        lines.append("提醒：" + "；".join(health.alerts))
    return "\n".join(lines)
