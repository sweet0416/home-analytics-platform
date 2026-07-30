from datetime import date, datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from app.core.config.settings import get_settings
from app.core.database.session import SessionLocal
from app.plugins.fund.application.services import FundService
from app.plugins.fund.infrastructure.persistence.repositories import FundRepository

TIMEZONE = "Asia/Shanghai"
JOB_ID = "fund_nav_auto_sync"

_scheduler: BackgroundScheduler | None = None
_last_run: dict[str, object] | None = None
_completed_date: date | None = None


def start_fund_scheduler() -> None:
    settings = get_settings()
    if not settings.fund_nav_auto_sync_enabled:
        logger.info("Fund NAV auto sync is disabled.")
        return

    global _scheduler
    if _scheduler is not None and _scheduler.running:
        logger.info("Fund NAV auto sync scheduler is already running.")
        return

    scheduler = BackgroundScheduler(timezone=TIMEZONE)
    scheduler.add_job(
        _run_scheduled_fund_nav_sync,
        CronTrigger.from_crontab(settings.fund_nav_sync_cron, timezone=TIMEZONE),
        id=JOB_ID,
        name="Fund NAV auto sync",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    _scheduler = scheduler
    logger.info("Fund NAV auto sync scheduler started: {}", settings.fund_nav_sync_cron)


def stop_fund_scheduler() -> None:
    global _scheduler
    if _scheduler is None:
        return
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Fund NAV auto sync scheduler stopped.")
    _scheduler = None


def get_fund_scheduler_status() -> dict[str, object]:
    settings = get_settings()
    job = _scheduler.get_job(JOB_ID) if _scheduler is not None else None
    return {
        "enabled": settings.fund_nav_auto_sync_enabled,
        "running": bool(_scheduler is not None and _scheduler.running),
        "cron": settings.fund_nav_sync_cron,
        "timezone": TIMEZONE,
        "next_run_at": job.next_run_time if job and job.next_run_time else None,
        "last_run": _last_run,
    }


def _run_scheduled_fund_nav_sync() -> None:
    global _completed_date, _last_run
    now = datetime.now(ZoneInfo(TIMEZONE))
    if _completed_date == now.date():
        message = "Fund NAV sync skipped because new NAV data was already saved today."
        logger.info(message)
        _last_run = {
            "status": "succeeded",
            "started_at": now,
            "finished_at": now,
            "total": 0,
            "succeeded": 0,
            "failed": 0,
            "updated": 0,
            "skipped": True,
            "message": message,
        }
        return

    db = SessionLocal()
    try:
        logger.info("Starting scheduled fund NAV sync.")
        settings = get_settings()
        service = FundService(FundRepository(db), settings=settings)
        result = service.sync_tracked_navs()
        if result.updated > 0:
            _completed_date = now.date()
        status = "succeeded" if result.failed == 0 else "partial"
        message = (
            f"Fund NAV sync finished: {result.succeeded}/{result.total} succeeded, "
            f"{result.updated} updated, {result.failed} failed."
        )
        logger.info(message)
        _last_run = {
            "status": status,
            "started_at": now,
            "finished_at": datetime.now(ZoneInfo(TIMEZONE)),
            "total": result.total,
            "succeeded": result.succeeded,
            "failed": result.failed,
            "updated": result.updated,
            "skipped": False,
            "message": message,
        }
    except Exception as exc:
        logger.exception("Scheduled fund NAV sync failed: {}", exc)
        _last_run = {
            "status": "failed",
            "started_at": now,
            "finished_at": datetime.now(ZoneInfo(TIMEZONE)),
            "total": 0,
            "succeeded": 0,
            "failed": 0,
            "updated": 0,
            "skipped": False,
            "message": f"Fund NAV sync failed: {exc}",
        }
    finally:
        db.close()
